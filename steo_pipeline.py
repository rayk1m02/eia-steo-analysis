import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os

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

def compute_correlation(df, series_id, api_key, lags=[1,3,6,12], start_year=None):
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

  lag_header = ["Crude_Price"] + [f"Crude_Price_Lag{lag}" for lag in lags]
  res = []

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

  return df_res, df_summary

def generate_graph(df):
  df_graph = df.set_index("Date")[["EF_Vol", "PB_Vol", "US_Vol"]]
  plt.figure(figsize=(10,6))
  df_graph.plot(ax=plt.gca())
  plt.title("Crude Oil Production Volume: Eagle Ford, Permian, and US Total")
  plt.ylabel("Million Barrels per Day")
  plt.xlabel("Date")
  plt.tight_layout()
  plt.show()

def export_results(df, filename, index=True):
  df.to_csv(filename, index=index)

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("EIA_TOKEN")

    records = extract_steo_data(["COPREF", "COPRPM", "COPRPUS"], api_key)
    df = clean(records)
    df = reshape(df)

    df_yearly = compute_metrics(df, metrics=["pct_share", "growth_rate", "mean_threshold", "zscore"])
    df_corr, df_corr_summary = compute_correlation(df, ["WTIPUUS"], api_key, lags=[1,3,6,12], start_year=2020)

    generate_graph(df)

    export_results(df_yearly, "output/texas_production_and_share.csv")
    export_results(df_corr_summary, "output/texas_production_price_correlation.csv")