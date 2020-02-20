"""
Copyright (C) Microsoft Corporation. All rights reserved.​
 ​
Microsoft Corporation (“Microsoft”) grants you a nonexclusive, perpetual,
royalty-free right to use, copy, and modify the software code provided by us
("Software Code"). You may not sublicense the Software Code or any use of it
(except to your affiliates and to vendors to perform work on your behalf)
through distribution, network access, service agreement, lease, rental, or
otherwise. This license does not purport to express any claim of ownership over
data you may have shared with Microsoft in the creation of the Software Code.
Unless applicable law gives you more rights, Microsoft reserves all other
rights not expressly granted herein, whether by implication, estoppel or
otherwise. ​
 ​
THE SOFTWARE CODE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
MICROSOFT OR ITS LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THE SOFTWARE CODE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

import os, json
from azureml.core import Workspace
from azureml.core.compute import DsvmCompute
from azureml.exceptions import ComputeTargetException
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
dsvm_settings = settings["compute_target"]["training"]["dsvm"]

# Get workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
config_file_path = os.environ.get("GITHUB_WORKSPACE", default="aml_service")
config_file_name = "aml_arm_config.json"
ws = Workspace.from_config(
    path=config_file_path,
    auth=cli_auth,
    _file_name=config_file_name)
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep = '\n')

try:
    print("Loading existing and attached DSVM")
    dsvm_compute = DsvmCompute(workspace=ws, name=dsvm_settings["name"])
    print("Found existing VM")
    if dsvm_compute.vm_size != dsvm_settings["vm_size"] or dsvm_compute.location != dsvm_settings["location"]:
        dsvm_compute.delete()
        dsvm_compute.wait_for_completion(show_output=True)
        raise ComputeTargetException("VM is of incorrect size or was deployed in a different location. Deleting VM and provisioning a new one.")
except ComputeTargetException:
    print("Loading failed")
    print("Creating and attaching new DSVM")
    dsvm_config = DsvmCompute.provisioning_configuration(vm_size=dsvm_settings["vm_size"])
    if dsvm_settings["location"]:
        dsvm_config.location = dsvm_settings["location"]
    if dsvm_settings["ssh_port"]:
        dsvm_config.ssh_port = dsvm_settings["ssh_port"]
    
    # Create Compute Target
    dsvm_compute = DsvmCompute.create(workspace=ws, name=dsvm_settings["name"], provisioning_configuration=dsvm_config)

    # Wait until the VM is attached
    dsvm_compute.wait_for_completion(show_output=True)

# Checking status of DSVM
print("Checking status of DSVM")
if dsvm_compute.provisioning_state == "Failed":
    dsvm_compute.delete()
    raise Exception(
        "Deployment of DSVM failed with the following status: {} and logs: \n{}".format(
            dsvm_compute.provisioning_state, dsvm_compute.provisioning_errors
        )
    )