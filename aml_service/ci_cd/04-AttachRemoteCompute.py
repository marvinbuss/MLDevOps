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
from azureml.core.compute import ComputeTarget, RemoteCompute
from azureml.core.compute_target import ComputeTargetException
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
remotecompute_settings = settings["compute_target"]["remotecompute"]

# Get workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep = '\n')

try:
    # Loading remote compute
    print("Loading existing and attached compute resource")
    remote_compute = RemoteCompute(workspace=ws, name=remotecompute_settings["name"])
    print("Found existing VM")
except ComputeTargetException:
    print("Loading failed")
    print("Trying to attach existing compute")

    # Create the compute config
    attach_config = RemoteCompute.attach_configuration(
        address=remotecompute_settings["address"],
        ssh_port=remotecompute_settings["ssh_port"],
        username=remotecompute_settings["address"]
        )
    if remotecompute_settings["use_ssh_auth"]:
        # use ssh authentication
        attach_config.password = None
        attach_config.private_key_file = remotecompute_settings["private_key_file"]
        attach_config.private_key_passphrase = remotecompute_settings["private_key_passphrase"]
    else:
        # use username and password authentication
        attach_config.password = remotecompute_settings["password"]
    
    # Attach the compute
    remote_compute = ComputeTarget.attach(ws, remotecompute_settings["name"], attach_config)

remote_compute.wait_for_completion(show_output=True)