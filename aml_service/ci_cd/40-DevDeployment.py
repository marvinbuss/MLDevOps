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
import os, sys, json
from azureml.core import Workspace, Image
from azureml.core.webservice import Webservice, AciWebservice
from azureml.exceptions import WebserviceException 
from azureml.core.authentication import AzureCliAuthentication

sys.path.insert(0, os.path.join("code", "testing"))
import test_functions

# Load the JSON settings file and relevant sections
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
deployment_settings = settings["deployment"]
aci_settings = deployment_settings["dev_deployment"]

# Loading Model Profile
print("Loading Model Profile")
with open(os.path.join("aml_service", "profiling_result.json")) as f:
    profiling_result = json.load(f)

# Get Workspace
print("Loading Workspace")
cli_auth = AzureCliAuthentication()
ws = Workspace.from_config(path=workspace_config_settings["path"], auth=cli_auth, _file_name=workspace_config_settings["file_name"])
print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep="\n")

# Loading Image
image_details = profiling_result["image_id"].split(":")
image = Image(workspace=ws,
              name=image_details[0],
              version=image_details[1])

# Deploying model on ACI
print("Deploying model on ACI")
try:
    print("Trying to update existing ACI service")
    dev_service = AciWebservice(workspace=ws, name=aci_settings["name"])
    dev_service.update(image=image,
                       tags=deployment_settings["image"]["tags"],
                       properties=deployment_settings["image"]["properties"],
                       description=deployment_settings["image"]["description"],
                       auth_enabled=aci_settings["auth_enabled"],
                       ssl_enabled=aci_settings["ssl_enabled"],
                       ssl_cert_pem_file=aci_settings["ssl_cert_pem_file"],
                       ssl_key_pem_file=aci_settings["ssl_key_pem_file"],
                       ssl_cname=aci_settings["ssl_cname"],
                       enable_app_insights=aci_settings["enable_app_insights"])
    print("Successfully updated existing ACI service")
except WebserviceException:
    print("Failed to update ACI service... Creating new ACI instance")
    aci_config = AciWebservice.deploy_configuration(cpu_cores=profiling_result["cpu"],
                                                    memory_gb=profiling_result["memory"],
                                                    tags=deployment_settings["image"]["tags"],
                                                    properties=deployment_settings["image"]["properties"],
                                                    description=deployment_settings["image"]["description"],
                                                    location=aci_settings["location"],
                                                    auth_enabled=aci_settings["auth_enabled"],
                                                    ssl_enabled=aci_settings["ssl_enabled"],
                                                    ssl_cert_pem_file=aci_settings["ssl_cert_pem_file"],
                                                    ssl_key_pem_file=aci_settings["ssl_key_pem_file"],
                                                    ssl_cname=aci_settings["ssl_cname"],
                                                    enable_app_insights=aci_settings["enable_app_insights"],
                                                    dns_name_label=aci_settings["dns_name_label"])
    
    # Deploying dev web service from image
    dev_service = Webservice.deploy_from_image(workspace=ws,
                                               name=aci_settings["name"],
                                               image=image,
                                               deployment_config=aci_config)
# Show output of the deployment on stdout
dev_service.wait_for_deployment(show_output=True)
print(dev_service.state)

# Checking status of web service
print("Checking status of ACI Dev Deployment")
if dev_service.state != "Healthy":
    raise Exception(
        "Dev Deployment on ACI failed with the following status: {} and logs: \n{}".format(
            dev_service.state, dev_service.get_logs()
        )
    )

# Testing ACI web service
print("Testing ACI web service")
test_sample = test_functions.get_test_data_sample()
print("Test Sample: ", test_sample)
test_sample_encoded = bytes(test_sample, encoding='utf8')
try:
    prediction = dev_service.run(input_data=test_sample)
    print(prediction)
except Exception as e:
    result = str(e)
    logs = dev_service.get_logs()
    dev_service.delete()
    raise Exception("ACI Dev web service is not working as expected: \n{} \nLogs: \n{}".format(result, logs))

# Delete aci after test
print("Deleting ACI Dev web service after successful test")
dev_service.delete()