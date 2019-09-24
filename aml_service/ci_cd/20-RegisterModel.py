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
import os, json, sys, azureml.core
from azureml.core import Workspace, Experiment, Run
from azureml.core.model import Model
from azureml.core.authentication import AzureCliAuthentication

# Load the JSON settings file and relevant section
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
deployment_settings = settings["deployment"]

# Get details from Run
print("Loading Run Details")
with open(os.path.join("aml_service", "run_details.json")) as f:
    run_details = json.load(f)

# Get Workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep = '\n')

# Loading Run
print("Loading Run")
experiment = Experiment(workspace=ws, name=run_details["experiment_name"])
run = Run(experiment=experiment, run_id=run_details["run_id"])

# Only register model, if it performs better than the production model
print("Register model only if it performs better.")
try:
    # Loading run of production model
    print("Loading Run of Production Model to evaluate new model")
    production_model = Model(workspace=ws, name=deployment_settings["model"]["name"])
    production_model_run_id = production_model.tags.get(["run_id"])
    production_model_run = Run(experiment=experiment, run_id=production_model_run_id)

    # Comparing models
    print("Comparing Metrics of production and newly trained model")
    promote_new_model = True
    for metric in deployment_settings["model"]["evaluation_parameters"]["larger_is_better"]:
        if not promote_new_model:
            break
        new_model_parameter = run.get_metrics().get(metric)
        production_model_parameter = production_model_run.get_metrics().get(metric)
        if new_model_parameter < production_model_parameter:
            promote_new_model = False
    for metric in deployment_settings["model"]["evaluation_parameters"]["smaller_is_better"]:
        if not promote_new_model:
            break
        new_model_parameter = run.get_metrics().get(metric)
        production_model_parameter = production_model_run.get_metrics().get(metric)
        if new_model_parameter > production_model_parameter:
            promote_new_model = False

    if promote_new_model:
        print("New model performs better, thus it will be registered")
    else:
        print("New model does not perform better.")
except:
    promote_new_model = True
    print("This is the first model to be trained, thus nothing to evaluate for now")

# Registering new Model
if promote_new_model:
    print("Registering new Model")
    tags = deployment_settings["model"]["tags"]
    tags = tags.update({"run_id": run.id})
    model = run.register_model(model_name=deployment_settings["model"]["name"],
                               model_path=deployment_settings["model"]["path"],
                               tags=tags,
                               properties=deployment_settings["model"]["properties"],
                               model_framework=deployment_settings["model"]["model_framework"],
                               model_framework_version=deployment_settings["model"]["model_framework_version"],
                               description=deployment_settings["model"]["description"],
                               datasets=deployment_settings["model"]["datasets"])
else:
    print("No new model to register thus no need to create new scoring image")
    #raise Exception('No new model to register as production model perform better')
    sys.exit(0)