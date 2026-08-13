#%%
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("EIA_TOKEN")

url = "https://api.eia.gov/v2/steo/data/"
'''
Filter conditions:
data[] - value (as seen in chart data)
facets[seriesID] - Crude oil production in Eagle Ford, Permian, and US
frequency - Monthly
sort by most recent dates (desc)
max rows 5000
'''
params = {
  "api_key": api_key,
  "data[]": "value",
  "facets[seriesId][]": ["COPREF", "COPRPM", "COPRPUS"],
  "frequency": "monthly",
  "sort[0][column]": "period",
  "sort[0][direction]": "desc",
  "length": 5000,
}

response = requests.get(url, params=params)
response.status_code

data = response.json()
data
# %%
