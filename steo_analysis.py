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
data[] - "value" (as seen in chart data)
facets[seriesID] - Crude oil production in Eagle Ford (COPREF), Permian (COPRPM), and US (COPRPUS)
frequency - "monthly"
sort by most recent dates
max rows 5000
'''
params = {
  "api_key": api_key,
  "data[]": "value",
  "facets[seriesId][]": ["COPREF", "COPRPM", "COPRPUS"],
  #"facets[seriesId][]": ["COPRPUS"],
  "frequency": "monthly",
  "sort[0][column]": "period",
  "sort[0][direction]": "desc",
  "length": 5000,
}

response = requests.get(url, params=params)
response.status_code

data = response.json()
data

data.keys()
data["request"]
data["response"].keys()
data["response"]["data"]
# data["response"]["total"]

'''
DATA PLAN
- We have a list of data points, each containing the YYYY-MM, Location, Crude Volume, Unit (million bbls/day)
- These datapoints span from 1990-01 up to 2027-12
- OBJECTIVES/LEARNINGS:
  - create a DataFrame and convert dtypes to datetime, numeric, etc as needed
  - analysis against US total crude production (%)
    - year by year what was the % of Permian and Eagle Ford against US Crude Production? individually and combined?
    - compute year-over-year growth rate per region. .pct_change()
  - programmatically find month to month dips or significant production margins (threshold of over 1.5x the mean)
    - use z-score instead for each month and compare 
    - compute .rolling() average and then measure dips against the trend line
      - then do some research to see what world events might have caused them
  - correlation with crude oil price, pull WTI/Brent price series and use method .corr()
    - production usually lags price changes (drilling takes months), .shift() a few months before correlating and analyze
  - line chart / graph that displays crude production volume across the three regions
  - export findings to csv file
  - refactor code into functions, make this a real reusable pipeline (at the basic level)
'''

''' create a DataFrame and convert dtypes to datetime, numeric, etc as needed '''
datapoints = data["response"]["data"]
type(datapoints)
datapoints
{key: type(value) for key, value in datapoints[0].items()}

# {'period': str,
# 'seriesId': str,
# 'seriesDescription': str,
# 'value': str,
# 'unit': str}

# pd DataFrames expect a list of dicts as one of its stsandard inputs. each dict becoming a row and the keys the columns.
df_steo = pd.DataFrame(datapoints)
df_steo
df_steo["period"] = pd.to_datetime(df_steo["period"])
df_steo["value"] = pd.to_numeric(df_steo["value"])
df_steo.dtypes
df_steo
df_steo = df_steo.rename(columns={
  "period": "Date", 
  "SeriesID": "ID",
  "SeriesDescription": "Description",
  "value": "Value",
  "unit": "Unit"
  })
df_steo
df_steo.dtypes
# Date                 datetime64[us]
# SeriesID                        str
# SeriesDescription               str
# Value                       float64
# Unit                            str
# dtype: object

''' 
analysis against US total crude production (%) 
  A) year by year what was the % of Permian and Eagle Ford against US Crude Production? individually and combined?
  B) compute year-over-year growth rate per region. .pct_change()
'''
# desired output for part A:
# Year PermianVolume EagleFordVolume USVolume PermianVolumePct EagelFordVolumePct CombinedPct
# 2027
# 2026
# 2025
df_yearly = df_steo.copy()                                        
df_yearly.insert(                                                 # extract and add the Year as as column next to Date
  loc=df_yearly.columns.get_loc("Date")+1,
  column="Year",
  value=df_yearly["Date"].dt.year
)
df_yearly                                                         
df_tx = df_yearly[df_yearly["ID"].isin(["COPREF", "COPRPM"])]    # grab only Eagle Ford and Permian
df_tx
df_steo_pct = df_tx.pivot_table(                                 # This builds out the first three columns of our desired dataframe (to some degree)
  values="Value",                                                # ID   COPREF  COPRPM
  index="Year",                                                  # Year
  columns="ID",                                                  # YYYY    x      y
  aggfunc="mean"
  )
df_steo_pct