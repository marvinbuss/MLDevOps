"""
Copyright (C) Microsoft Corporation. All rights reserved.​

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
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.exceptions import ComputeTargetException
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
aml_settings = settings["compute_target"]["training"]["amlcompute"]

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
    # Loading AMLCompute
    print("Loading existing AML Compute")
    cluster = AmlCompute(workspace=ws, name=aml_settings["name"])

    # Check settings and redeploy if required settings have changed
    print("Found existing cluster")
    if cluster.vm_size.lower() != aml_settings["vm_size"].lower() or cluster.vm_priority.lower() != aml_settings["vm_priority"].lower():
        cluster.delete()
        cluster.wait_for_completion(show_output=True)
        raise ComputeTargetException("Cluster is of incorrect size or has incorrect priority. Deleting cluster and provisioning a new one.")
    
    # Update AMLCompute
    #if cluster.provisioning_configuration.min_nodes != aml_settings["min_nodes"] or cluster.provisioning_configuration.max_nodes != aml_settings["max_nodes"] or cluster.provisioning_configuration.idle_seconds_before_scaledown != aml_settings["idle_seconds_before_scaledown"]:
    print("Updating settings of Cluster")
    cluster.update(min_nodes=aml_settings["min_nodes"],
                   max_nodes=aml_settings["max_nodes"],
                   idle_seconds_before_scaledown=aml_settings["idle_seconds_before_scaledown"])
    
    # Wait until the operation has completed
    cluster.wait_for_completion(show_output=True)
    
    print("Successfully updated Cluster definition")
except ComputeTargetException:
    print("Loading failed")
    print("Creating new AML Compute resource")
    compute_config = AmlCompute.provisioning_configuration(vm_size=aml_settings["vm_size"],
                                                           vm_priority=aml_settings["vm_priority"],
                                                           min_nodes=aml_settings["min_nodes"],
                                                           max_nodes=aml_settings["max_nodes"],
                                                           idle_seconds_before_scaledown=aml_settings["idle_seconds_before_scaledown"],
                                                           tags=aml_settings["tags"],
                                                           description=aml_settings["description"])
    
    # Deploy to VNET if provided 
    if aml_settings["vnet_resource_group_name"] and aml_settings["vnet_name"] and aml_settings["subnet_name"]:
        compute_config.vnet_resourcegroup_name = aml_settings["vnet_resource_group_name"]
        compute_config.vnet_name = aml_settings["vnet_name"]
        compute_config.subnet_name = aml_settings["subnet_name"]
    
    # Set Credentials if provided
    if aml_settings["admin_username"] and aml_settings["admin_user_password"]:
        compute_config.admin_username = aml_settings["admin_username"]
        compute_config.admin_user_password = aml_settings["admin_user_password"]
    elif aml_settings["admin_username"] and aml_settings["admin_user_ssh_key"]:
        compute_config.admin_username = aml_settings["admin_username"]
        compute_config.admin_user_ssh_key = aml_settings["admin_user_ssh_key"]
    
    # Create Compute Target
    cluster = ComputeTarget.create(workspace=ws, name=aml_settings["name"], provisioning_configuration=compute_config)

    # Wait until the cluster is attached
    cluster.wait_for_completion(show_output=True)

# Checking status of AMLCompute Cluster
print("Checking status of AMLCompute Cluster")
if cluster.provisioning_state == "Failed":
    cluster.delete()
    raise Exception(
        "Deployment of AMLCompute Cluster failed with the following status: {} and logs: \n{}".format(
            cluster.provisioning_state, cluster.provisioning_errors
        )
    )