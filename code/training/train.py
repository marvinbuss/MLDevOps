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
import pickle
from azureml.core import Workspace
from azureml.core.run import Run
import os
from sklearn.datasets import load_diabetes
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.externals import joblib
import numpy as np
import json
import subprocess
from typing import Tuple, List

RANDOM_STATE = 42
MODEL_NAME = "my-model.pkl"

print("Creating output folder")
os.makedirs('./outputs', exist_ok=True)

print("Getting Run context")
run = Run.get_context()

print("Loading data")
X, y = load_diabetes(return_X_y=True)

print("Creating train test split")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
data = {"train": {"X": X_train, "y": y_train}, "test": {"X": X_test, "y": y_test}}

print("Training a ridge regression model with sklearn and random alpha value")
alphas = np.arange(0.0, 1.0, 0.05)
alpha = alphas[np.random.choice(alphas.shape[0], 1, replace=False)][0]

reg = Ridge(alpha=alpha)
reg.fit(data["train"]["X"], data["train"]["y"])
preds = reg.predict(data["test"]["X"])
mse = mean_squared_error(preds, data["test"]["y"])
print("Alpha is {0:.2f}, and MSE is {1:0.2f}".format(alpha, mse))

print("Logging values")
run.log("alpha", alpha)
run.log("mse", mse)

print("Saving model to output folder")
with open(MODEL_NAME, "wb") as file:
    joblib.dump(value=reg, filename=os.path.join("./outputs/", MODEL_NAME))

print("Training successful")
