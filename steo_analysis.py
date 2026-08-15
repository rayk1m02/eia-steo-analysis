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
  - programmatically find year to year dips or significant production margins (threshold of over 1.5x the mean)
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
  "seriesId": "ID",
  "seriesDescription": "Description",
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
# desired output for year by year %
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
df_steo_pct = df_tx.pivot_table(                                 # This builds out the first three columns of our desired dataframe
  values="Value",                                                # ID   COPREF  COPRPM
  index="Year",                                                  # Year
  columns="ID",                                                  # YYYY    x      y
  aggfunc="mean"
  )
df_steo_pct
df_steo_pct.columns                                     # Index(['COPREF', 'COPRPM'], dtype='str', name='ID')
df_steo_pct = df_steo_pct.rename_axis(columns=None)     # Remove "ID" label sitting on top of "Year" index
df_steo_pct
df_steo_pct = df_steo_pct.rename(columns={"COPREF": "EagleFordVol", "COPRPM": "PermianVol"})
df_steo_pct
# Appending USVolume to our df_steo_pct dataframe
df_us = df_yearly[df_yearly["ID"].isin(["COPRPUS"])]
df_us
df_us_pivot = df_us.pivot_table(
  values="Value",
  index="Year",
  columns="ID",
  aggfunc="mean"
)
df_us_pivot
df_us_pivot = df_us_pivot.rename_axis(columns=None)
df_us_pivot = df_us_pivot.rename(columns={"COPRPUS": "USVol"})
df_us_pivot
# use .merge()
df_steo_pct = df_steo_pct.merge(df_us_pivot, on="Year")
df_steo_pct
# Appending EagleFordPct, PermianPct, and CombinedPct
df_steo_pct["EagleFordPct"] = (df_steo_pct["EagleFordVol"] / df_steo_pct["USVol"]) * 100
df_steo_pct["PermianPct"] = (df_steo_pct["PermianVol"] / df_steo_pct["USVol"]) * 100
df_steo_pct["CombinedPct"] = ((df_steo_pct["EagleFordVol"] + df_steo_pct["PermianVol"]) / df_steo_pct["USVol"]) * 100
df_steo_pct.style.format({
  "EagleFordPct": "{:.1f}%",
  "PermianPct": "{:.1f}%",
  "CombinedPct": "{:.1f}%"
})
df_steo_pct
# compute year-over-year growth rate per region. .pct_change()
df_steo_pct["EagleFordGrowthRate"] = df_steo_pct["EagleFordVol"].pct_change() * 100
df_steo_pct["PermianGrowthRate"] = df_steo_pct["PermianVol"].pct_change() * 100
df_steo_pct["USGrowthRate"] = df_steo_pct["USVol"].pct_change() * 100
df_steo_pct
df_steo_pct.style.format({
  "EagleFordPct": "{:.1f}%",
  "PermianPct": "{:.1f}%",
  "CombinedPct": "{:.1f}%",
  "EagleFordGrowthRate": "{:.1f}%",
  "PermianGrowthRate": "{:.1f}%",
  "USGrowthRate": "{:.1f}%",
})

'''   
- programmatically find year to year dips or significant production margins (threshold of over 1.5x the mean)
    - use z-score instead for each year and compare 
    - compute .rolling() average and then measure dips against the trend line
      - then do research on what world events might have caused these dips
'''
# obtain absolute value of the growth rate
# compute mean of the absolute values
# filter df_steo_pct for rows where abs_val exceeed 1.5 * mean
df_steo_dips = df_steo_pct.reset_index()[["Year", "EagleFordGrowthRate", "PermianGrowthRate", "USGrowthRate"]].copy()
df_steo_dips
df_steo_dips["EagleFordAbs"] = df_steo_dips["EagleFordGrowthRate"].abs()
df_steo_dips["PermianAbs"] = df_steo_dips["PermianGrowthRate"].abs()
df_steo_dips["USAbs"] = df_steo_dips["USGrowthRate"].abs()
df_steo_dips
  # col_data = df_steo_dips["PermianAbs"]
  # df_steo_dips = df_steo_dips.drop(columns=["PermianAbs"])
  # df_steo_dips.insert(
  #   loc=df_steo_dips.columns.get_loc("EagleFordAbs") + 1,
  #   column="PermianAbs",
  #   value=col_data
  # )
  # df_steo_dips = df_steo_dips.drop(columns=["PermianGrowthAbs"])
  # df_steo_dips
df_steo_dips["EagleFordAbs"].mean() # 32.8582
df_steo_dips["PermianAbs"].mean()   # 12.0359
df_steo_dips["USAbs"].mean()        # 7.3733
df_steo_dips
# the .mean() on the absolute values tells us the magnitude of the year-over-year swings in either direction.
# now, find which years had a swing greater than 1.5x the mean for the respective regions
df_steo_dips = df_steo_dips.round(2)
df_steo_dips
df_steo_dips = df_steo_dips.rename(columns={
                  "EagleFordGrowthRate": "EF_GrowthRate",
                  "PermianGrowthRate": "PB_GrowthRate",
                  "USGrowthRate": "US_GrowthRate",
                  "EagleFordAbs": "EF_Abs",
                  "PermianAbs": "PB_Abs",
                  "USAbs": "US_Abs"
                })
df_steo_dips
df_steo_dips["EF_Threshold"] = df_steo_dips["EF_Abs"] > df_steo_dips["EF_Abs"].mean() * 1.5
df_steo_dips["PB_Threshold"] = df_steo_dips["PB_Abs"] > df_steo_dips["PB_Abs"].mean() * 1.5
df_steo_dips["US_Threshold"] = df_steo_dips["US_Abs"] > df_steo_dips["US_Abs"].mean() * 1.5
df_steo_dips
df_steo_threshold = df_steo_dips[
  df_steo_dips["EF_Threshold"] | df_steo_dips["PB_Threshold"] | df_steo_dips["US_Threshold"]
].copy()
df_steo_threshold     # Years where production margin was > 1.5x the mean

# From the results, we can infer that Eagle Ford drove the early shale boom, with significant percentage swings of up to 217% in 2011, while the Permian Basin became the dominant producer from 2014 onwards. We can also infer that percentage swings shrink as a base grows.

# - use z-score instead for each year and compare 

# Z-score is the conventional, recognized way to account for spread. We will use z-score instead of the arbitrary 1.5x mean threshold to find statistical outliers. Z-score is computed by (value - mean) / standard_deviation.
df_steo_z = df_steo_dips.copy()
df_steo_z["EF_z"] = (df_steo_z["EF_Abs"] - df_steo_z["EF_Abs"].mean()) / df_steo_z["EF_Abs"].std()
df_steo_z["PB_z"] = (df_steo_z["PB_Abs"] - df_steo_z["PB_Abs"].mean()) / df_steo_z["PB_Abs"].std()
df_steo_z["US_z"] = (df_steo_z["US_Abs"] - df_steo_z["US_Abs"].mean()) / df_steo_z["US_Abs"].std()
df_steo_z = df_steo_z.round(2)
df_steo_z
# filter by any Threshold columns with True in it or z score columns that have abs() > 1.5 (looser cutoff for initial exploration)
df_steo_z_filtered = df_steo_z[
  df_steo_z["EF_Threshold"] | 
  df_steo_z["PB_Threshold"] | 
  df_steo_z["US_Threshold"] | 
  (df_steo_z["EF_z"].abs() > 1.5) |
  (df_steo_z["PB_z"].abs() > 1.5) |
  (df_steo_z["US_z"].abs() > 1.5)
].copy()
df_steo_z_filtered
# applying stricter cutoff with +- 2 z-score threshold
df_steo_z_filtered_strict = df_steo_z_filtered[
  # df_steo_z["EF_Threshold"] | 
  # df_steo_z["PB_Threshold"] | 
  # df_steo_z["US_Threshold"] | 
  (df_steo_z_filtered["EF_z"].abs() > 2) |
  (df_steo_z_filtered["PB_z"].abs() > 2) |
  (df_steo_z_filtered["US_z"].abs() > 2)
].copy()
df_steo_z_filtered_strict

# Our results show 2011 and 2018 as the only years with a z_score > 2. 2011 indicates Eagle Ford's outlier (growth rate of 217.37%) and 2018 indicates Permian's outlier with a growth rate of 39.74%. Each play had its own distinct, statistically significant growth years and is also consistent with Eagle Ford's earlier boom and Permian's later, larger one.

# we are going to drop .rolling() average for now, as we have the mean and z-score analysis fairly consistent with each others findings. 
# rolling average answers a more local question of how a certain year behaved relative to its immediate surrounding years. How was this year unusual relative to what was already happening around it? instead of using the play's entire history.

#   - do research on what world events might have caused these dips
# 2011 Eagle Ford: production surged six-fold over the year as horizontal drilling paths were completed and hydraulic fracturing expanded across STX. Over 2800 drilling permits where issued and rig and well completions were accelerating production. 
# 2018 Permian Basin: operators routinely drilled "super-lateral" extensions (streching 2-3 miles instead of 1 mile like in 2011). Also there was an increase in scale of completions to open up oil-bearing shale. The Permian is also multi layered, and operators mastered pad drilling (using a single surface rig to drill dozen horizontal wells in different subterranean layers simultaneously). All of this caused a major infrastructure crisis in 2018 as there were pipeline shortages (too much oil) and subsequently local prices collapsed ($15-$18 less a barrel!) than the U.S. benchmark pricing. Also operators had to burn off significant amounts of natural gas just to keep the oil flowing.
