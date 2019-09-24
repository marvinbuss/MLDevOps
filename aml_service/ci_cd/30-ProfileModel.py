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
import os, json, azureml.core
from azureml.core import Workspace, ContainerRegistry, Environment
from azureml.core.model import Model, InferenceConfig
from azureml.core.image import Image, ContainerImage
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file and relevant section
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
deployment_settings = settings["deployment"]

# Get Workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep="\n")

# Loading Model
print("Loading Model")
model = Model(workspace=ws, name=deployment_settings["model"]["name"])

# Create image registry configuration 
if deployment_settings["image"]["docker"]["custom_image"]:
    container_registry = ContainerRegistry()
    container_registry.address = deployment_settings["image"]["docker"]["custom_image_registry_details"]["address"]
    container_registry.username = deployment_settings["image"]["docker"]["custom_image_registry_details"]["username"]
    container_registry.password = deployment_settings["image"]["docker"]["custom_image_registry_details"]["password"]
else:
    container_registry = None

# Profile model
print("Profiling Model")
test_sample = json.dumps({'data': [[1,2,3,4,5,6,7,8,9,10]]})
inference_config = InferenceConfig(entry_script=deployment_settings["image"]["entry_script"],
                                   source_directory=deployment_settings["image"]["source_directory"],
                                   runtime=deployment_settings["image"]["runtime"],
                                   conda_file=deployment_settings["image"]["conda_file"],
                                   extra_docker_file_steps=deployment_settings["image"]["docker"]["extra_docker_file_steps"],
                                   enable_gpu=deployment_settings["image"]["docker"]["use_gpu"],
                                   description=deployment_settings["image"]["description"],
                                   base_image=deployment_settings["image"]["docker"]["custom_image"],
                                   base_image_registry=container_registry,
                                   cuda_version=deployment_settings["image"]["docker"]["cuda_version"])
profile = Model.profile(ws, "githubactionsprofiling", [model], inference_config, test_sample)
profile.wait_for_profiling(True)
print(profile.get_results(), profile.recommended_cpu, profile.recommended_cpu_latency, profile.recommended_memory, profile.recommended_memory_latency, sep="\n")
#TODO: Enable custom environment and register environment

# Create Docker Image
print("Creating Docker Image")
package = Model.package(workspace=ws, models=[model], inference_config=inference_config, generate_dockerfile=True)
package.wait_for_creation(show_output=True)

# Writing the profiling results to /aml_service/profiling_result.json
profiling_result = {}
profiling_result["cpu"] = profile.recommended_cpu
profiling_result["memory"] = profile.recommended_memory
with open(os.path.join("aml_service", "profiling_result.json"), "w") as outfile:
    json.dump(profiling_result, outfile)
