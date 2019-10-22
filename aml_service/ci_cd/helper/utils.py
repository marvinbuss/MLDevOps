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
from azureml.core import Environment
from azureml.core.environment import CondaDependencies
from azureml.train.hyperdrive import BanditPolicy, MedianStoppingPolicy, NoTerminationPolicy, TruncationSelectionPolicy
from azureml.train.hyperdrive import RandomParameterSampling, GridParameterSampling, BayesianParameterSampling
from azureml.train.hyperdrive import choice, randint, uniform, quniform, loguniform, qloguniform, normal, qnormal, lognormal, qlognormal
from azureml.exceptions import RunConfigurationException


def get_environment(name_suffix="_training"):
    # Load the JSON settings file
    print("Loading settings")
    with open(os.path.join("aml_config", "settings.json")) as f:
        settings = json.load(f)
    env_settings = settings["environment"]
    env_name = settings["experiment"]["name"]  + name_suffix

    # Create Dependencies
    print("Defining Conda Dependencies")
    conda_dep = CondaDependencies().create(
        pip_indexurl=None,
        pip_packages=env_settings["pip_packages"],
        conda_packages=env_settings["conda_packages"],
        python_version=env_settings["python_version"],
        pin_sdk_version=env_settings["pin_sdk_version"]
        )
    conda_dep.save(path=env_settings["dependencies_config"]["path"])

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
    return env


def get_parameter_sampling(sampling_method, parameter_settings):
    parameter_dict = {}
    for parameter_name, parameter_setting in parameter_settings.items():
        parameter_distr = get_parameter_distribution(parameter_name, parameter_setting)
        parameter_dict["--{}".format(parameter_name)] = parameter_distr

    if "random" in sampling_method:
        ps = RandomParameterSampling(parameter_dict)
    elif "grid" in sampling_method:
        ps = GridParameterSampling(parameter_dict)
    elif "bayesian" in sampling_method:
        ps = BayesianParameterSampling(parameter_dict)
    else:
        ps = None
        raise RunConfigurationException("Parameter Sampling Method not defined in settings. Please choose between \'random\', \'grid\' and \'bayesian\'")
    return ps


def get_parameter_distribution(parameter_name, parameter_setting):
    if "choice" in parameter_setting["distribution"]:
        parameter_distr = choice(parameter_setting["parameters"]["options"])
    elif "randint" in parameter_setting["distribution"]:
        parameter_distr = randint(upper=parameter_setting["parameters"]["upper"])
    elif "uniform" in parameter_setting["distribution"]:
        parameter_distr = uniform(min_value=parameter_setting["parameters"]["min_value"], max_value=parameter_setting["parameters"]["max_value"])
    elif "quniform" in parameter_setting["distribution"]:
        parameter_distr = quniform(min_value=parameter_setting["parameters"]["min_value"], max_value=parameter_setting["parameters"]["max_value"], q=parameter_setting["parameters"]["q"])
    elif "loguniform" in parameter_setting["distribution"]:
        parameter_distr = loguniform(min_value=parameter_setting["parameters"]["min_value"], max_value=parameter_setting["parameters"]["max_value"])
    elif "qloguniform" in parameter_setting["distribution"]:
        parameter_distr = qloguniform(min_value=parameter_setting["parameters"]["min_value"], max_value=parameter_setting["parameters"]["max_value"], q=parameter_setting["parameters"]["q"])
    elif "normal" in parameter_setting["distribution"]:
        parameter_distr = normal(mu=parameter_setting["parameters"]["mu"], sigma=parameter_setting["parameters"]["sigma"])
    elif "qnormal" in parameter_setting["distribution"]:
        parameter_distr = qnormal(mu=parameter_setting["parameters"]["mu"], sigma=parameter_setting["parameters"]["sigma"], q=parameter_setting["parameters"]["q"])
    elif "lognormal" in parameter_setting["distribution"]:
        parameter_distr = lognormal(mu=parameter_setting["parameters"]["mu"], sigma=parameter_setting["parameters"]["sigma"])
    elif "qlognormal" in parameter_setting["distribution"]:
        parameter_distr = qlognormal(mu=parameter_setting["parameters"]["mu"], sigma=parameter_setting["parameters"]["sigma"], q=parameter_setting["parameters"]["q"])
    else:
        parameter_distr = None
        raise RunConfigurationException("Parameter distribution for parameter {} not defined in settings. Please choose between \'choice\', \'randint\', \'uniform\', \'quniform\', \'loguniform\', \'qloguniform\', \'normal\', \'qnormal\', \'lognormal\' and \'qlognormal\'".format(parameter_name))
    return parameter_distr

def get_policy(policy_settings):
    if "bandit" in policy_settings["name"]:
        policy = BanditPolicy(evaluation_interval=policy_settings["evaluation_interval"],
                              delay_evaluation=policy_settings["delay_evaluation"],
                              slack_factor=policy_settings["bandit"]["slack_factor"],
                              slack_amount=policy_settings["bandit"]["slack_amount"])
    elif "medianstopping" in policy_settings["name"]:
        policy = MedianStoppingPolicy(evaluation_interval=policy_settings["evaluation_interval"],
                                      delay_evaluation=policy_settings["delay_evaluation"])
    elif "noterminal" in policy_settings["name"]:
        policy = NoTerminationPolicy()
    elif "truncationselection" in policy_settings["name"]:
        policy = TruncationSelectionPolicy(evaluation_interval=policy_settings["evaluation_interval"],
                                           delay_evaluation=policy_settings["delay_evaluation"],
                                           truncation_percentage=policy_settings["truncationselection"]["truncation_percentage"])
    else:
        policy = None
    return policy