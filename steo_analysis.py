#%%
import requests
import pandas as pd
from dotenv import load_dotenv
import os
import matplotlib.pyplot as plt

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
    - then do some research to see what world events might have caused them
  - correlate crude price series (WTI/Brent) against production volumes at zero lag as baseline, then lag intervals of (1,3,6 months) to see if delay strengthens the relationship. We are testing whether production responds to price changes only after drilling catches up.
    - methods: .corr(), .shift()
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
# 2011 Eagle Ford: 
  # Production surged six-fold over the year as horizontal drilling paths were completed and hydraulic fracturing expanded across STX. 
  # Over 2800 drilling permits where issued and rig and well completions were accelerating production. 
# 2018 Permian Basin: 
  # Operators routinely drilled "super-lateral" extensions (streching 2-3 miles instead of 1 mile like in 2011). 
  # Also there was an increase in scale of completions to open up oil-bearing shale. The Permian is multi layered, and operators mastered pad drilling (using a single surface rig to drill dozen horizontal wells in different subterranean layers simultaneously).
  # All of this caused a major infrastructure crisis in 2018 as there were pipeline shortages (too much oil) and subsequently local prices collapsed ($15-$18 less a barrel!) than the U.S. benchmark pricing. 
  # Operators also had to burn off significant amounts of natural gas just to keep the oil flowing.
# 2014 US Total:
  # We see that the US experienced one of its largest volume increaess (z-score of 2.58) due to rapid expansion of the domestic shale boom. 

'''
- correlate crude price series (WTI/Brent) against production volumes at zero lag as baseline, then lag intervals of (1,3,6,12 months) to see if delay strengthens the relationship. We are testing whether production responds to price changes only after drilling catches up.
  - methods: .corr(), .shift()
'''
'''
output
df_steo_lag
Date        EF_Vol     PB_Vol       US_Vol   Crude_Price    Crude_Price_Lag1    Crude_Price_Lag2    Crude_Price_Lag 3
YYYY-MM-DD    
'''
df_steo_crude = df_steo.copy()
df_steo_crude 
df_steo_crude = df_steo_crude.pivot_table(
    values="Value",
    index="Date",
    columns="ID",
    aggfunc="sum"
  )
df_steo_crude
df_steo_crude = df_steo_crude.rename(columns={
  "COPREF": "EF_Vol",
  "COPRPM": "PB_Vol",
  "COPRPUS": "US_Vol"
})
df_steo_crude = df_steo_crude.rename_axis(columns=None) # Get rid of "ID" axis name
df_steo_crude = df_steo_crude.sort_index()
df_steo_crude = df_steo_crude.round(3)
df_steo_crude

# Pulling WTI Crude Oil Price (West Texas Intermediate)
param_WTI = {
  "api_key": api_key,
  "data[]": "value",
  "facets[seriesId][]": ["WTIPUUS"],
  "frequency": "monthly",
  "sort[0][column]": "period",
  "sort[0][direction]": "desc",
  "length": 5000,
}
response_WTI = requests.get(url, params=param_WTI)
data_WTI = response_WTI.json()
data_WTI.keys()
data_WTI["response"].keys()
data_crude_price = data_WTI["response"]["data"]
data_crude_price
df_crude_price = pd.DataFrame(data_crude_price)
df_crude_price["period"] = pd.to_datetime(df_crude_price["period"])
df_crude_price["value"] = pd.to_numeric(df_crude_price["value"])
df_crude_price = df_crude_price.rename(columns={
  "period": "Date",
  "seriesId": "ID",
  "seriesDescription": "Description",
  "value": "Value",
  "unit": "Unit"
})
df_crude_price.dtypes
df_crude_price

# Merge df_steo_crude with df_crude_price. Append the Value (price) and match on Date field. 
df_steo_crude = df_steo_crude.reset_index()
df_steo_crude_merged = df_steo_crude.merge(
  df_crude_price[["Date", "Value"]],
  on="Date"
)
df_steo_crude_merged = df_steo_crude_merged.rename(columns={"Value":"Crude_Price"})
df_steo_crude_merged

# .shift(x) brings the values down by x. So .shift(1) would have each date correspond to the previous months crude price

df_steo_crude_merged["Crude_Price_Lag1"] = df_steo_crude_merged["Crude_Price"].shift(1)
df_steo_crude_merged["Crude_Price_Lag3"] = df_steo_crude_merged["Crude_Price"].shift(3)
df_steo_crude_merged["Crude_Price_Lag6"] = df_steo_crude_merged["Crude_Price"].shift(6)
df_steo_crude_merged["Crude_Price_Lag12"] = df_steo_crude_merged["Crude_Price"].shift(12)
df_steo_crude_merged

# .corr() - +1 indicates positive relationship, 0 no relationship, -1 negative relationship

# Eagle Ford
df_steo_crude_merged["EF_Vol"].corr(df_steo_crude_merged["Crude_Price"]) # -0.2773124592336688
df_steo_crude_merged["EF_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag1"]) # -0.23355681868684805
df_steo_crude_merged["EF_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag3"]) # -0.19249605853744672
df_steo_crude_merged["EF_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag6"]) # -0.1843092117464142
df_steo_crude_merged["EF_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag12"]) # -0.14554095573179343

# Permian Basin
df_steo_crude_merged["PB_Vol"].corr(df_steo_crude_merged["Crude_Price"]) # -0.09642829972633593
df_steo_crude_merged["PB_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag1"]) # -0.08499699968042564
df_steo_crude_merged["PB_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag3"]) # -0.08866294837861996
df_steo_crude_merged["PB_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag6"]) # -0.12300799989103951
df_steo_crude_merged["PB_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag12"]) # -0.17936447790183874

# USA
df_steo_crude_merged["US_Vol"].corr(df_steo_crude_merged["Crude_Price"]) # 0.2994777836229339
df_steo_crude_merged["US_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag1"]) # 0.30931135201190657
df_steo_crude_merged["US_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag3"]) # 0.32345528594977335
df_steo_crude_merged["US_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag6"]) # 0.3457113314492093
df_steo_crude_merged["US_Vol"].corr(df_steo_crude_merged["Crude_Price_Lag12"]) # 0.38076234228994393

# Price alone is a weak indicator of production across the board.
# The shape of the weakness differs by region, however. 
# US Totals show a modest lagged relationship that indicates the "drilling takes time" notion.
# Permian shows an unstable relationship, perhaps growth is more so driven by infrastructure than price response.
# Eagle Ford shows a persistent negative relationship.

''' - line chart / graph that displays crude production volume across the three regions '''
df_steo_crude = df_steo_crude.set_index("Date")
df_steo_crude
plt.figure(figsize=(10,6))
df_steo_crude.plot(ax=plt.gca())
plt.title("Crude Oil Production Volume: Eagle Ford, Permian, and US Total")
plt.ylabel("Million Barrels per Day")
plt.xlabel("Date")
plt.tight_layout()
plt.show()

''' - export findings to csv file '''
# which dataframes should be exported to csv?
df_steo_pct.to_csv("output/texas_production_and_share.csv", index=True)
df_steo_crude_merged.to_csv("output/texas_production_price_correlation.csv", index=True)

''' - refactor code into functions, make this a real reusable pipeline (at the basic level) '''
# Pull data from API
# Clean data
# Reshape data
# Compute metrics
# Compute correlation
# Generate graph
# Export

# Pull data from API
def extract_steo_data(series_ids, api_key):
  url = "https://api.eia.gov/v2/steo/data/"
  params = {
    "api_key": api_key,
    "data[]": "value",
    "facets[seriesId][]": series_ids,
    "frequency": "monthly",
    "sort[0][column]": "period",
    "sort[0][direction]": "desc",
    "length": 5000,
  }
  response = requests.get(url, params=params)
  response.raise_for_status()
  data = response.json()
  return data["response"]["data"]

records = extract_steo_data(["COPREF", "COPRPM", "COPRPUS"], api_key)

# Clean data
def clean(records):
  df = pd.DataFrame(records)
  df["period"] = pd.to_datetime(df["period"])
  df["value"] = pd.to_numeric(df["value"])
  df = df.rename(columns={
    "period": "Date",
    "seriesId": "ID",
    "seriesDescription": "Description",
    "value": "Value",
    "unit": "Unit"
  })
  return df

# Reshape data
def reshape(df):
  df = df.pivot_table(
    index="Date",
    values="Value",
    columns="ID"
  )
  df = df.rename_axis(columns=None)
  df = df.rename(columns={
    "COPREF": "EF_Vol",
    "COPRPM": "PB_Vol",
    "COPRPUS": "US_Vol",
    "WTIPUUS": "Crude_Price"
  })
  df = df.reset_index()
  df.insert(
    loc=df.columns.get_loc("Date")+1,
    column="Year",
    value=df["Date"].dt.year
  )
  return df

df = clean(records)
df
df = reshape(df)
df

# Compute metrics
def compute_metrics(df, metrics=["pct_share", "growth_rate", "mean_threshold", "zscore"]):
  df = df.groupby("Year")[["EF_Vol", "PB_Vol", "US_Vol"]].mean().reset_index()
  if "pct_share" in metrics:
    df["EF_Pct"] = df["EF_Vol"] / df["US_Vol"] * 100
    df["PB_Pct"] = df["PB_Vol"] / df["US_Vol"] * 100
    df["Combined_Pct"] = (df["EF_Vol"] + df["PB_Vol"]) / df["US_Vol"] * 100
  if "growth_rate" in metrics:
    df["EF_GrowthRate"] = df["EF_Vol"].pct_change() * 100
    df["PB_GrowthRate"] = df["PB_Vol"].pct_change() * 100
    df["US_GrowthRate"] = df["US_Vol"].pct_change() * 100
  if "mean_threshold" in metrics:
    df["EF_Threshold"] = df["EF_GrowthRate"].abs() > df["EF_GrowthRate"].abs().mean() * 1.5
    df["PB_Threshold"] = df["PB_GrowthRate"].abs() > df["PB_GrowthRate"].abs().mean() * 1.5
    df["US_Threshold"] = df["US_GrowthRate"].abs() > df["US_GrowthRate"].abs().mean() * 1.5
  if "zscore" in metrics:
    df["EF_Z"] = (df["EF_GrowthRate"].abs() - df["EF_GrowthRate"].abs().mean()) / df["EF_GrowthRate"].abs().std()
    df["PB_Z"] = (df["PB_GrowthRate"].abs() - df["PB_GrowthRate"].abs().mean()) / df["PB_GrowthRate"].abs().std()
    df["US_Z"] = (df["US_GrowthRate"].abs() - df["US_GrowthRate"].abs().mean()) / df["US_GrowthRate"].abs().std()
  return df.round(2)

df_yearly = compute_metrics(df, metrics=["pct_share", "growth_rate", "mean_threshold", "zscore"])
df_yearly
df_yearly.style.format({
    "EF_Threshold": lambda x: "True" if x else "",
    "PB_Threshold": lambda x: "True" if x else "",
    "US_Threshold": lambda x: "True" if x else "",
}, na_rep="")

# Compute correlation
def compute_correlation(df, series_id, lags=[1,3,6,12], start_year=None):
  # call extract_steo_data(), clean(), and reshape() on series_id (essentially a price series)
  # df - this needs to be df pre-compute_metrics()
  records_price = extract_steo_data(series_id, api_key)
  df_price = clean(records_price)
  df_price = reshape(df_price)
  df_res = df.merge(df_price[["Date", "Crude_Price"]], on="Date")

  if 1 in lags:
    df_res["Crude_Price_Lag1"] = df_res["Crude_Price"].shift(1)
  if 3 in lags:
    df_res["Crude_Price_Lag3"] = df_res["Crude_Price"].shift(3)
  if 6 in lags:
    df_res["Crude_Price_Lag6"] = df_res["Crude_Price"].shift(6)
  if 12 in lags:
    df_res["Crude_Price_Lag12"] = df_res["Crude_Price"].shift(12)

  # create a summary dataframe for correlation coefficients

  # Lag                 EF_Corr PB_Corr US_Corr
  # Crude_Price
  # Crude_Price_Lag1
  # Crude_Price_Lag2
  # Crude_Price_Lag3

  # lag_header = [
  #   "Crude_Price", 
  #   "Crude_Price_Lag1", 
  #   "Crude_Price_Lag3", 
  #   "Crude_Price_Lag6", 
  #   "Crude_Price_Lag12"
  #   ]
  lag_header = ["Crude_Price"] + [f"Crude_Price_Lag{lag}" for lag in lags]

  res = []

  # [{"Lag": lag_header[i], "EF_Corr": 0.321, "PB_Corr": 0.324, "US_Corr": 0.432},
  #  {"Lag": lag_header[i+1], "EF_Corr": 0.331, "PB_Corr": 0.321, "US_Corr": 0.231},
  #  ...
  # ]

  for lag in lag_header:
    lag_row = {
      "Lag": lag,
      "EF_Corr": df_res["EF_Vol"].corr(df_res[lag]),
      "PB_Corr": df_res["PB_Vol"].corr(df_res[lag]),
      "US_Corr": df_res["US_Vol"].corr(df_res[lag])
    }
    res.append(lag_row)

  df_summary = pd.DataFrame(res).round(3)

  if start_year is not None:
    df_res = df_res[df_res["Date"].dt.year >= start_year]
    
  # numeric_cols = ["EF_Vol", "PB_Vol", "US_Vol", "Crude_Price"] + [f"Crude_Price_Lag{lag}" for lag in lags]
  # df[numeric_cols] = df[numeric_cols].round(2)
  return df_res, df_summary

df_monthly = clean(records)
df_monthly = reshape(df_monthly)
df_monthly
df_monthly, df_summary = compute_correlation(df_monthly, ["WTIPUUS"], lags=[1,3,6,12], start_year=2020)

float_cols = df_monthly.select_dtypes(include="float").columns
df_monthly.style.format({col: "{:.2f}" for col in float_cols}, na_rep="")

df_summary

# Generate graph
def generate_graph(df):
  df_graph = df.set_index("Date")[["EF_Vol", "PB_Vol", "US_Vol"]]
  plt.figure(figsize=(10,6))
  df_graph.plot(ax=plt.gca())
  plt.title("Crude Oil Production Volume: Eagle Ford, Permian, and US Total")
  plt.ylabel("Million Barrels per Day")
  plt.xlabel("Date")
  plt.tight_layout()
  plt.show()

generate_graph(df)

# Export
def export_results(df, filename, index=True):
  df.to_csv(filename, index=index)

# Create eia_steo_pipeline.py