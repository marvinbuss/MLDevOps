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
import pickle, json, time
import numpy as np
from sklearn.externals import joblib
from sklearn.linear_model import Ridge
from azureml.core.model import Model
from azureml.monitoring import ModelDataCollector
#from inference_schema.schema_decorators import input_schema, output_schema
#from inference_schema.parameter_types.numpy_parameter_type import NumpyParameterType

def init():
    global model
    print("Model Initialized: " + time.strftime("%H:%M:%S"))
    # load the model from file into a global object
    model_path = Model.get_model_path(model_name="mymodel")
    model = joblib.load(model_path)
    print("Initialize Data Collectors")
    global inputs_dc, prediction_dc
    inputs_dc = ModelDataCollector(model_name="sklearn_regression_model", feature_names=["AGE", "SEX", "BMI", "BP", "S1", "S2", "S3", "S4", "S5", "S6"])
    prediction_dc = ModelDataCollector(model_name="sklearn_regression_model", feature_names=["Y"])

#input_sample = np.array([[10.0,9.0,8.0,7.0,6.0,5.0,4.0,3.0,2.0,1.0]])
#output_sample = np.array([3726.995])

#@input_schema('data', NumpyParameterType(input_sample))
#@output_schema(NumpyParameterType(output_sample))
def run(raw_data):
    global inputs_dc, prediction_dc
    try:
        data = json.loads(raw_data)["data"]
        data = np.array(data)
        result = model.predict(data)

        print("Saving Data " + time.strftime("%H:%M:%S"))
        inputs_dc.collect(data)
        prediction_dc.collect(result)

        return json.dumps({"result": result.tolist()})
    except Exception as e:
        error = str(e)
        print(error + time.strftime("%H:%M:%S"))
        return json.dumps({"error": error})