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
from azureml.core import Workspace, Experiment, ContainerRegistry, Environment
from azureml.core.compute import ComputeTarget
from azureml.core.compute_target import ComputeTargetException
from azureml.core.runconfig import MpiConfiguration, TensorflowConfiguration
from azureml.core.authentication import AzureCliAuthentication
from azureml.train.dnn import Chainer, PyTorch, TensorFlow, Gloo, Nccl
from azureml.train.sklearn import SKLearn
from azureml.train.estimator import Estimator
from azureml.train.hyperdrive import HyperDriveConfig, PrimaryMetricGoal
from helper import utils

# Load the JSON settings file and relevant section
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
experiment_settings = settings["experiment"]
compute_target_to_use = settings["compute_target"]["compute_target_to_use"].strip().lower()
compute_target_name = settings["compute_target"][compute_target_to_use]["name"]
workspace_config_settings = settings["workspace"]["config"]

# Get workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep = '\n')

# Attach Experiment
print("Loading Experiment")
exp = Experiment(workspace=ws, name=experiment_settings["name"])
print(exp.name, exp.workspace.name, sep="\n")

# Load compute target
print("Loading Compute Target")
compute_target = ComputeTarget(workspace=ws, name=compute_target_name)

# Create image registry configuration 
if experiment_settings["docker"]["custom_image"]:
    container_registry = ContainerRegistry()
    container_registry.address = experiment_settings["docker"]["custom_image_registry_details"]["address"]
    container_registry.username = experiment_settings["docker"]["custom_image_registry_details"]["username"]
    container_registry.password = experiment_settings["docker"]["custom_image_registry_details"]["password"]
else:
    container_registry = None

# Create disributed training configuration
if experiment_settings["distributed_training"]["backend_config"] == "mpi":
    distrib_training_backend = MpiConfiguration()
    distrib_training_backend.process_count_per_node = experiment_settings["distributed_training"]["mpi"]["process_count_per_node"]
elif experiment_settings["distributed_training"]["backend_config"] == "parameter_server":
    distrib_training_backend = TensorflowConfiguration()
    distrib_training_backend.worker_count = experiment_settings["distributed_training"]["parameter_server"]["worker_count"]
    distrib_training_backend.parameter_server_count = experiment_settings["distributed_training"]["parameter_server"]["parameter_server_count"]
elif experiment_settings["distributed_training"]["backend_config"] == "glue":
    distrib_training_backend = Gloo()
elif experiment_settings["distributed_training"]["backend_config"] == "nccl":
    distrib_training_backend = Nccl()
else:
    distrib_training_backend = None

# Create Estimator for Experiment
print("Creating Estimator object according to settings")
if experiment_settings["framework"]["name"] == "chainer":
    framework_version = experiment_settings["framework"]["chainer"]["framework_version"]
    enable_optimized_mode = experiment_settings["framework"]["chainer"]["_enable_optimized_mode"]

    estimator = Chainer(
        source_directory=experiment_settings["source_directory"],
        compute_target=compute_target,
        entry_script=experiment_settings["entry_script"],
        script_params=experiment_settings["script_parameters"],
        node_count=experiment_settings["distributed_training"]["node_count"],
        distributed_training=distrib_training_backend,
        use_gpu=experiment_settings["docker"]["use_gpu"],
        use_docker=experiment_settings["docker"]["use_docker"],
        custom_docker_image=experiment_settings["docker"]["custom_image"],
        image_registry_details=container_registry,
        user_managed=experiment_settings["user_managed"],
        conda_packages=experiment_settings["dependencies"]["conda_packages"],
        pip_packages=experiment_settings["dependencies"]["pip_packages"],
        conda_dependencies_file=experiment_settings["dependencies"]["conda_dependencies_file"],
        pip_requirements_file=experiment_settings["dependencies"]["pip_requirements_file"],
        environment_variables=experiment_settings["environment_variables"],
        inputs=experiment_settings["data_references"],
        source_directory_data_store=experiment_settings["source_directory_datastore"],
        shm_size=experiment_settings["docker"]["shm_size"],
        max_run_duration_seconds=experiment_settings["max_run_duration_seconds"],
        framework_version=framework_version,
        _enable_optimized_mode=enable_optimized_mode)

elif experiment_settings["framework"]["name"] == "pytorch":
    framework_version = experiment_settings["framework"]["pytorch"]["framework_version"]
    enable_optimized_mode = experiment_settings["framework"]["pytorch"]["_enable_optimized_mode"]

    estimator = PyTorch(
        source_directory=experiment_settings["source_directory"],
        compute_target=compute_target,
        entry_script=experiment_settings["entry_script"],
        script_params=experiment_settings["script_parameters"],
        node_count=experiment_settings["distributed_training"]["node_count"],
        distributed_training=distrib_training_backend,
        use_gpu=experiment_settings["docker"]["use_gpu"],
        use_docker=experiment_settings["docker"]["use_docker"],
        custom_docker_image=experiment_settings["docker"]["custom_image"],
        image_registry_details=container_registry,
        user_managed=experiment_settings["user_managed"],
        conda_packages=experiment_settings["dependencies"]["conda_packages"],
        pip_packages=experiment_settings["dependencies"]["pip_packages"],
        conda_dependencies_file=experiment_settings["dependencies"]["conda_dependencies_file"],
        pip_requirements_file=experiment_settings["dependencies"]["pip_requirements_file"],
        environment_variables=experiment_settings["environment_variables"],
        inputs=experiment_settings["data_references"],
        source_directory_data_store=experiment_settings["source_directory_datastore"],
        shm_size=experiment_settings["docker"]["shm_size"],
        max_run_duration_seconds=experiment_settings["max_run_duration_seconds"],
        framework_version=framework_version,
        _enable_optimized_mode=enable_optimized_mode)
    
elif experiment_settings["framework"]["name"] == "tensorflow":
    framework_version = experiment_settings["framework"]["tensorflow"]["framework_version"]
    enable_optimized_mode = experiment_settings["framework"]["tensorflow"]["_enable_optimized_mode"]

    estimator = TensorFlow(
        source_directory=experiment_settings["source_directory"],
        compute_target=compute_target,
        entry_script=experiment_settings["entry_script"],
        script_params=experiment_settings["script_parameters"],
        node_count=experiment_settings["distributed_training"]["node_count"],
        distributed_training=distrib_training_backend,
        use_gpu=experiment_settings["docker"]["use_gpu"],
        use_docker=experiment_settings["docker"]["use_docker"],
        custom_docker_image=experiment_settings["docker"]["custom_image"],
        image_registry_details=container_registry,
        user_managed=experiment_settings["user_managed"],
        conda_packages=experiment_settings["dependencies"]["conda_packages"],
        pip_packages=experiment_settings["dependencies"]["pip_packages"],
        conda_dependencies_file=experiment_settings["dependencies"]["conda_dependencies_file"],
        pip_requirements_file=experiment_settings["dependencies"]["pip_requirements_file"],
        environment_variables=experiment_settings["environment_variables"],
        inputs=experiment_settings["data_references"],
        source_directory_data_store=experiment_settings["source_directory_datastore"],
        shm_size=experiment_settings["docker"]["shm_size"],
        max_run_duration_seconds=experiment_settings["max_run_duration_seconds"],
        framework_version=framework_version,
        _enable_optimized_mode=enable_optimized_mode)
    
elif experiment_settings["framework"]["name"] == "sklearn":
    framework_version = experiment_settings["framework"]["sklearn"]["framework_version"]
    enable_optimized_mode = experiment_settings["framework"]["sklearn"]["_enable_optimized_mode"]

    estimator = SKLearn(
        source_directory=experiment_settings["source_directory"],
        compute_target=compute_target,
        entry_script=experiment_settings["entry_script"],
        script_params=experiment_settings["script_parameters"],
        use_docker=experiment_settings["docker"]["use_docker"],
        custom_docker_image=experiment_settings["docker"]["custom_image"],
        image_registry_details=container_registry,
        user_managed=experiment_settings["user_managed"],
        conda_packages=experiment_settings["dependencies"]["conda_packages"],
        pip_packages=experiment_settings["dependencies"]["pip_packages"],
        conda_dependencies_file=experiment_settings["dependencies"]["conda_dependencies_file"],
        pip_requirements_file=experiment_settings["dependencies"]["pip_requirements_file"],
        environment_variables=experiment_settings["environment_variables"],
        inputs=experiment_settings["data_references"],
        shm_size=experiment_settings["docker"]["shm_size"],
        max_run_duration_seconds=experiment_settings["max_run_duration_seconds"],
        framework_version=framework_version,
        _enable_optimized_mode=enable_optimized_mode)
        
else:
    estimator = Estimator(
        source_directory=experiment_settings["source_directory"],
        compute_target=compute_target,
        entry_script=experiment_settings["entry_script"],
        script_params=experiment_settings["script_parameters"],
        node_count=experiment_settings["distributed_training"]["node_count"],
        process_count_per_node=experiment_settings["distributed_training"]["mpi"]["process_count_per_node"],
        distributed_training=distrib_training_backend,
        use_gpu=experiment_settings["docker"]["use_gpu"],
        use_docker=experiment_settings["docker"]["use_docker"],
        custom_docker_image=experiment_settings["docker"]["custom_image"],
        image_registry_details=container_registry,
        user_managed=experiment_settings["user_managed"],
        conda_packages=experiment_settings["dependencies"]["conda_packages"],
        pip_packages=experiment_settings["dependencies"]["pip_packages"],
        conda_dependencies_file=experiment_settings["dependencies"]["conda_dependencies_file"],
        pip_requirements_file=experiment_settings["dependencies"]["pip_requirements_file"],
        environment_variables=experiment_settings["environment_variables"],
        inputs=experiment_settings["data_references"],
        source_directory_data_store=experiment_settings["source_directory_datastore"],
        shm_size=experiment_settings["docker"]["shm_size"],
        max_run_duration_seconds=experiment_settings["max_run_duration_seconds"])

# Use custom Environment and keep old environment variables 
if experiment_settings["use_custom_environment"]:
    print("Setting Custom Environment Definition")
    env = utils.get_environment()
    old_env_variables = estimator._estimator_config.environment.environment_variables
    env.environment_variables.update(old_env_variables)
    estimator._estimator_config.environment = env
print(estimator.run_config)

# Register Environment
print("Registering Environment")
env = estimator.run_config.environment
env.name = experiment_settings["name"]
registered_env = env.register(workspace=ws)
print("Registered Environment")
print(registered_env.name, "Version: " + registered_env.version, sep="\n")

# Creating HyperDriveConfig for Hyperparameter Tuning
if experiment_settings["hyperparameter_sampling"]["use_hyperparameter_sampling"]:
    print("Creating HyperDriveConfig for Hyperparameter Tuning")

    parameter_sampling = utils.get_parameter_sampling(experiment_settings["hyperparameter_sampling"]["method"], experiment_settings["hyperparameter_sampling"]["parameters"])
    policy = utils.get_policy(experiment_settings["hyperparameter_sampling"]["policy"])
    primary_metric_goal = PrimaryMetricGoal.MAXIMIZE if "max" in experiment_settings["hyperparameter_sampling"]["primary_metric_goal"] else PrimaryMetricGoal.MINIMIZE
    
    run_config = HyperDriveConfig(estimator=estimator,
                                  hyperparameter_sampling=parameter_sampling, 
                                  policy=policy,
                                  primary_metric_name=experiment_settings["hyperparameter_sampling"]["primary_metric_name"],
                                  primary_metric_goal=primary_metric_goal,
                                  max_total_runs=experiment_settings["hyperparameter_sampling"]["max_total_runs"],
                                  max_concurrent_runs=experiment_settings["hyperparameter_sampling"]["max_concurrent_runs"],
                                  max_duration_minutes=experiment_settings["hyperparameter_sampling"]["max_duration_minutes"])
else:
    run_config = estimator

# Submitting an Experiment and creating a Run
print("Submitting an experiment and creating a run")
run = exp.submit(run_config, tags=experiment_settings["run_tags"])

# Shows output of the run on stdout.
run.wait_for_completion(show_output=True, wait_post_processing=True)

# Raise exception if run fails
if run.get_status() == "Failed":
    raise Exception(
        "Training on local failed with following run status: {} and logs: \n {}".format(
            run.get_status(), run.get_details_with_logs()
        )
    )

# Writing the run id to /aml_config/run_id.json
# TODO: rework this
run_details = {}
run_details["run_id"] = run.id
run_details["experiment_name"] = run.experiment.name
with open(os.path.join("aml_service", "run_details.json"), "w") as outfile:
    json.dump(run_details, outfile)