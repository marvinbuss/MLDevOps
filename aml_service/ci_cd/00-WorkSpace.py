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

import os, json, sys, argparse
import azureml.core
from azureml.core import Workspace
from azureml.exceptions import WorkspaceException
from azureml.core.authentication import AzureCliAuthentication

print("SDK Version of azureml: ", azureml.core.VERSION)
print("Current directory: " + os.getcwd())

# Parse Arguments
print("Parsing arguments")
parser = argparse.ArgumentParser(description="Azure Machine Learning Service - CI/CD")
parser.add_argument("--subscription-id", type=str,  dest="subscription_id", help="ID of the Subscription that should be used")
parser.add_argument("--workspace-name", type=str,  dest="workspace_name", help="Name of the Azure Machine Learning Workscpace")
parser.add_argument("--resource-group", type=str,  dest="resource_group", help="Name of the Resource Group")
parser.add_argument("--location", type=str,  dest="location", help="Region in Azure")
parser.add_argument("--friendly-name", type=str,  dest="friendly_name", help="Friendly name of the Azure Machine Learning Workspace")
args = parser.parse_args()

# Mask values
print("Masking values")
print(f"::add-mask::{args.subscription_id}")

# Use Azure CLI authentication
cli_auth = AzureCliAuthentication()

try:
    print("Loading existing Workspace")
    ws = Workspace.get(
        name=args.workspace_name,
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        auth=cli_auth
    )
    print("Found existing Workspace")
except WorkspaceException:
    print("Loading failed")
    print("Creating new Workspace")
    ws = Workspace.create(
        name=args.workspace_name,
        auth=cli_auth,
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        location=args.location,
        create_resource_group=True,
        friendly_name=args.friendly_name,
        show_output=True
    )

# Write out the Workspace ARM properties to a config file
config_file_path = os.environ.get("GITHUB_WORKSPACE", default="aml_service")
print(f"File Path: {config_file_path}")
config_file_name = "aml_arm_config.json"
ws.write_config(
    path=config_file_path,
    file_name=config_file_name
)

# Print Workspace details --> only print, if repository is private
print("Workspace name: " + ws.name,
      "Azure region: " + ws.location,
      "Subscription id: " + ws.subscription_id,
      "Resource group: " + ws.resource_group, sep = '\n')
print("Successfully loaded Workspace")