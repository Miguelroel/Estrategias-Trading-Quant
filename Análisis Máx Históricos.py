# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 19:19:38 2021

@author: G&L
"""

import pandas as pd
import requests
import json
import numpy as np
import matplotlib.pyplot as plt

TOKEN = "DS0RGXA4B93RVQTG"
    
def getDailyAdj(symbol, outputsize):
    function = "TIME_SERIES_DAILY_ADJUSTED"
    url = "https://www.alphavantage.co/query"
    parametros = {"function": function, "symbol": symbol, "outputsize": outputsize, "apikey": TOKEN}
    
    r = requests.get(url, params = parametros)
    js = r.json()["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(js, orient = "index")
    df = df.astype("float")
    df.index.name = "Date"
    df = df.sort_values(by = "Date", ascending = True)
    df = df.round(2)
    df.columns = ["Open", "High", "Low", "Close", "AdjClose", "Volume", "Div", "Split"]
    df.index = pd.to_datetime(df.index)
    
    return df

tickers = ["AAPL", "AMZN", "NFLX", "MELI", "FB"]

fig, ax = plt.subplots(figsize = (16, 10))

for ticker in tickers:
    data = getDailyAdj(ticker, "full")
    data = data[["Open", "High", "Low", "AdjClose", "Volume"]]
    data["max"] = data["AdjClose"].cummax()
    data["max_v2"] = np.where(data["max"] != data["max"].shift(), data["max"], 0)
    data["max_historico"] = np.where((data["max_v2"] != 0) & (data["AdjClose"].shift(-1) < data["AdjClose"]) & 
                                 (data["AdjClose"].shift(-2) < data["AdjClose"].shift(-1)), data["max_v2"], 0)
    data = data.dropna()
    rsEjex = [i for i in range(2, 100)]
    rsmean = []
    for i in range(2, 100):
        data2 = data
        data2["Rend"] = np.where(data2["max_historico"] > 0, (data2["AdjClose"].shift(-i)/data2["AdjClose"]- 1) * 100, 0)
        data2 = data2[data2["Rend"] != 0]
        rsmean.append(data2["Rend"].mean())
    ax.plot(rsEjex, rsmean, lw = 2, label = ticker)    

ax.axhline(y = 0, color = "red", ls = "dashed")
ax.set_ylabel("Rendimiento porcentual")
ax.set_xlabel("Cantidad de ruedas posterior al máximo histórico")
fig.suptitle("Rendimientos desde máximos históricos seguidos de dos velas rojas", y = 0.95, fontsize = 14)
plt.legend( loc = "upper left")
plt.show()