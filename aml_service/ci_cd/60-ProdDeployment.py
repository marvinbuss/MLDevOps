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
from azureml.core import Workspace, Image
from azureml.core.webservice import Webservice, AksWebservice
from azureml.core.authentication import AzureCliAuthentication
from azureml.core.compute import AksCompute, ComputeTarget
from azureml.core.compute_target import ComputeTargetException

# Load the JSON settings file and relevant sections
print("Loading settings")
with open(os.path.join("aml_service", "settings.json")) as f:
    settings = json.load(f)
workspace_config_settings = settings["workspace"]["config"]
deployment_settings = settings["deployment"]
aks_service_settings = deployment_settings["prod_deployment"]
aks_compute_settings = settings["compute_target"]["deployment"]["aks_prod"]

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

try:
    # Loading existing Prod AKS Cluster
    print("Loading existing Prod AKS Cluster")
    aks_prod_cluster = AksCompute(workspace=ws, name=aks_compute_settings["name"])

    # Check settings and redeploy if required settings have changed
    print("Found existing cluster")
    #aks_prod_cluster.update()
    #print("Successfully updated Cluster definition")
except ComputeTargetException:
    print("Loading failed")
    print("Creating new Prod AKS Cluster")
    compute_config = AksCompute.provisioning_configuration(agent_count=aks_compute_settings["agent_count"],
                                                           vm_size=aks_compute_settings["vm_size"],
                                                           ssl_cname=aks_compute_settings["ssl_cname"],
                                                           ssl_cert_pem_file=aks_compute_settings["ssl_cert_pem_file"],
                                                           ssl_key_pem_file=aks_compute_settings["ssl_key_pem_file"],
                                                           location=aks_compute_settings["location"],
                                                           service_cidr=aks_compute_settings["service_cidr"],
                                                           dns_service_ip=aks_compute_settings["dns_service_ip"],
                                                           docker_bridge_cidr=aks_compute_settings["docker_bridge_cidr"],
                                                           cluster_purpose=AksCompute.ClusterPurpose.FAST_PROD)
    # Deploy to VNET if provided 
    if aks_compute_settings["vnet_resource_group_name"] and aks_compute_settings["vnet_name"] and aks_compute_settings["subnet_name"]:
        compute_config.vnet_resourcegroup_name = aks_compute_settings["vnet_resource_group_name"]
        compute_config.vnet_name = aks_compute_settings["vnet_name"]
        compute_config.subnet_name = aks_compute_settings["subnet_name"]
    
    # Create Compute Target
    aks_prod_cluster = ComputeTarget.create(workspace=ws, name=aks_compute_settings["name"], provisioning_configuration=compute_config)

# Wait until the cluster is attached
aks_prod_cluster.wait_for_completion(show_output=True)

# Checking status of Test AKS Cluster
print("Checking status of Test AKS Cluster")
if aks_prod_cluster.provisioning_state != "Succeeded":
    raise Exception(
        "Deployment of Test AKS Cluster failed with the following status: {} and logs: \n {}".format(
            aks_prod_cluster.provisioning_state, aks_prod_cluster.provisioning_errors
        )
    )
    #sys.exit(0)

# Deploying model on prod AKS
print("Deploying model on Prod AKS")
try:
    print("Trying to update existing Prod web service")
    prod_service = AksWebservice(workspace=ws, name=aks_service_settings["name"])
    prod_service.update(image=image,
                       autoscale_enabled=aks_service_settings["autoscale_enabled"],
                       autoscale_min_replicas=aks_service_settings["autoscale_min_replicas"],
                       autoscale_max_replicas=aks_service_settings["autoscale_max_replicas"],
                       autoscale_refresh_seconds=aks_service_settings["autoscale_refresh_seconds"],
                       autoscale_target_utilization=aks_service_settings["autoscale_target_utilization"],
                       collect_model_data=aks_service_settings["collect_model_data"],
                       auth_enabled=aks_service_settings["auth_enabled"],
                       cpu_cores=profiling_result["cpu"],
                       memory_gb=profiling_result["memory"],
                       enable_app_insights=aks_service_settings["enable_app_insights"],
                       scoring_timeout_ms=aks_service_settings["scoring_timeout_ms"],
                       replica_max_concurrent_requests=aks_service_settings["replica_max_concurrent_requests"],
                       max_request_wait_time=aks_service_settings["max_request_wait_time"],
                       num_replicas=aks_service_settings["num_replicas"],
                       tags=deployment_settings["image"]["tags"],
                       properties=deployment_settings["image"]["properties"],
                       description=deployment_settings["image"]["description"],
                       gpu_cores=aks_service_settings["gpu_cores"],
                       period_seconds=aks_service_settings["period_seconds"],
                       initial_delay_seconds=aks_service_settings["initial_delay_seconds"],
                       timeout_seconds=aks_service_settings["timeout_seconds"],
                       success_threshold=aks_service_settings["success_threshold"],
                       failure_threshold=aks_service_settings["failure_threshold"],
                       namespace=aks_service_settings["namespace"],
                       token_auth_enabled=aks_service_settings["token_auth_enabled"])
    print("Successfully updated existing AKS test service")
except:
    print("Failed to update AKS test service... Creating new AKS test service")
    aks_config = AksWebservice.deploy_configuration(autoscale_enabled=aks_service_settings["autoscale_enabled"],
                                                    autoscale_min_replicas=aks_service_settings["autoscale_min_replicas"],
                                                    autoscale_max_replicas=aks_service_settings["autoscale_max_replicas"],
                                                    autoscale_refresh_seconds=aks_service_settings["autoscale_refresh_seconds"],
                                                    autoscale_target_utilization=aks_service_settings["autoscale_target_utilization"],
                                                    collect_model_data=aks_service_settings["collect_model_data"],
                                                    auth_enabled=aks_service_settings["auth_enabled"],
                                                    cpu_cores=profiling_result["cpu"],
                                                    memory_gb=profiling_result["memory"],
                                                    enable_app_insights=aks_service_settings["enable_app_insights"],
                                                    scoring_timeout_ms=aks_service_settings["scoring_timeout_ms"],
                                                    replica_max_concurrent_requests=aks_service_settings["replica_max_concurrent_requests"],
                                                    max_request_wait_time=aks_service_settings["max_request_wait_time"],
                                                    num_replicas=aks_service_settings["num_replicas"],
                                                    primary_key=aks_service_settings["primary_key"],
                                                    secondary_key=aks_service_settings["secondary_key"],
                                                    tags=deployment_settings["image"]["tags"],
                                                    properties=deployment_settings["image"]["properties"],
                                                    description=deployment_settings["image"]["description"],
                                                    gpu_cores=aks_service_settings["gpu_cores"],
                                                    period_seconds=aks_service_settings["period_seconds"],
                                                    initial_delay_seconds=aks_service_settings["initial_delay_seconds"],
                                                    timeout_seconds=aks_service_settings["timeout_seconds"],
                                                    success_threshold=aks_service_settings["success_threshold"],
                                                    failure_threshold=aks_service_settings["failure_threshold"],
                                                    namespace=aks_service_settings["namespace"],
                                                    token_auth_enabled=aks_service_settings["token_auth_enabled"])
    
    # Deploying prod web service from image
    prod_service = Webservice.deploy_from_image(workspace=ws,
                                                name=aks_service_settings["name"],
                                                image=image,
                                                deployment_config=aks_config,
                                                deployment_target=aks_prod_cluster)
# Show output of the deployment on stdout
prod_service.wait_for_deployment(show_output=True)
print(prod_service.state)

# Checking status of prod web service
print("Checking status of AKS Prod Deployment")
if prod_service.state != "Healthy":
    raise Exception(
        "Prod Deployment on AKS failed with the following status: {} and logs: \n{}".format(
            prod_service.state, prod_service.get_logs()
        )
    )
    #sys.exit(0)

# Testing AKS web service
print("Testing AKS prod web service")
test_sample = json.dumps({'data': [[1,2,3,4,5,6,7,8,9,10]]})
print("Test Sample: ", test_sample)
test_sample_encoded = bytes(test_sample, encoding='utf8')
try:
    prediction = prod_service.run(input_data=test_sample)
    print(prediction)
except Exception as e:
    result = str(e)
    raise Exception("AKS Prod web service is not working as expected: \n{}".format(result))