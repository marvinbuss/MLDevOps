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
import os, json, azureml.core
from azureml.core import Workspace, Environment
from azureml.core.environment import CondaDependencies
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file
print("Loading settings")
with open(os.path.join("aml_config", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
env_settings = settings["environment"]
env_name = settings["experiment"]["environment_name"]

'''
env_name = settings["experiment"]["environment_name"]
python_version = settings["environment"]["python_version"]
conda_packages = settings["environment"]["conda_packages"]
pip_packages = settings["environment"]["pip_packages"]
pin_sdk_version = settings["environment"]["pin_sdk_version"]
env_variables = settings["environment"]["env_variables"]
user_managed_dependencies = settings["environment"]["user_managed_dependencies"]
docker_enabled = settings["environment"]["docker"]["enabled"]
docker_gpu_support = settings["environment"]["docker"]["gpu_support"]
docker_arguments = settings["environment"]["docker"]["arguments"]
docker_mpi_image = settings["environment"]["docker"]["mpi_image"]
docker_base_image = settings["environment"]["docker"]["base_image"]
docker_base_image_registry_address = settings["environment"]["docker"]["base_image_registry"]["address"].strip()
docker_base_image_registry_username = settings["environment"]["docker"]["base_image_registry"]["username"].strip()
docker_base_image_registry_password = settings["environment"]["docker"]["base_image_registry"]["password"].strip()
docker_shared_volumes = settings["environment"]["docker"]["shared_volumes"]
docker_shm_size = settings["environment"]["docker"]["shm_size"].strip()
'''

# Get workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep = '\n')

# Create Dependencies
print("Defining Conda Dependencies")
conda_dep = CondaDependencies().create(
    pip_indexurl=None,
    pip_packages=env_settings["pip_packages"],
    conda_packages=env_settings["conda_packages"],
    python_version=env_settings["python_version"],
    pin_sdk_version=env_settings["pin_sdk_version"]
    )
conda_dep.save_to_file(env_settings["dependencies_config"]["path"], conda_file_path=env_settings["dependencies_config"]["file_name"])

# Create Environment and setting parameters
print("Creating Environment")
env = Environment(name=env_name)
env.python.conda_dependencies = conda_dep
env.environment_variables = env_settings["env_variables"]

if env_settings["user_managed_dependencies"]:
    print("Using existing user-managed Python environment for run")
    env.user_managed_dependencies = env_settings["user_managed_dependencies"]
elif env_settings["docker"]["enabled"]:
    print("Using Docker run with system-built conda environment based on dependency specification")
    env.docker.enabled = env_settings["docker"]["enabled"]
    env.docker.gpu_support = env_settings["docker"]["gpu_support"]
    env.docker.arguments = env_settings["docker"]["arguments"]
    env.docker.shared_volumes = env_settings["docker"]["shared_volumes"]
    env.docker.shm_size = env_settings["docker"]["shm_size"]

    if env_settings["docker"]["gpu_support"] and env_settings["docker"]["mpi_image"]:
        env.docker.base_image = azureml.core.runconfig.MPI_GPU_IMAGE
    elif env_settings["docker"]["gpu_support"]:
        env.docker.base_image = azureml.core.runconfig.DEFAULT_GPU_IMAGE
    elif env_settings["docker"]["mpi_image"]:
        env.docker.base_image = azureml.core.runconfig.MPI_CPU_IMAGE
    
    env.docker.base_image = env_settings["docker"]["base_image"]
    env.docker.base_image_registry.address = env_settings["docker"]["base_image_registry"]["address"]
    env.docker.base_image_registry.username = env_settings["docker"]["base_image_registry"]["username"]
    env.docker.base_image_registry.password = env_settings["docker"]["base_image_registry"]["password"]
else:
    print("Using system-build conda environment based on dependency specification")
    env.docker.enabled = False

# Register Environment
print("Registering Environment in Workspace")
registered_env = env.register(workspace=ws)

# Save details of Environment to load correct version 
env_details = {}
env_details["name"] = registered_env.name
env_details["version"] = registered_env.version
with open(os.path.join("aml_config", "env_details.json"), "w") as outfile:
    json.dump(env_details, outfile)