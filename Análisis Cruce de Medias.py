# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 20:16:34 2021

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


def EMA(symbol, time_period, interval = "daily", series_type = "close"):
    function = "EMA"
    url = "https://www.alphavantage.co/query"
    parametros = {"function": function, "symbol": symbol, "interval": interval, "series_type": series_type, "time_period": time_period,
                  "apikey": TOKEN}
    
    r = requests.get(url, params = parametros)
    js = r.json()["Technical Analysis: EMA"]
    df = pd.DataFrame.from_dict(js, orient = "index")
    df = df.astype("float")
    df.index.name = "Date"
    df = df.sort_values(by = "Date", ascending = True)
    df = df.round(2)
    df.columns = ["EMA " + str(time_period)]
    df.index = pd.to_datetime(df.index)
    return df


def tabla(symbol, fastema, slowema):
    data = getDailyAdj(symbol, "full")
    data = data[["Open", "High", "Low", "AdjClose", "Volume"]]
    fastema = EMA(symbol, fastema)
    slowema = EMA(symbol, slowema)
    dataTOT = pd.concat([data, fastema, slowema], axis = 1)
    dataTOT = dataTOT.dropna()
    return dataTOT


fast = 10
slow = 50
symbol = "MELI"

data = tabla(symbol, fast, slow)
data["Buy"] = (data["EMA " + str(fast)] > data["EMA " + str(slow)]) & (data["EMA " + str(fast)].shift() < data["EMA " + str(slow)].shift())
data["Sell"] = (data["EMA " + str(fast)] < data["EMA " + str(slow)]) & (data["EMA " + str(fast)].shift() > data["EMA " + str(slow)].shift())
data["Resta"] = 0
data = data.reset_index(drop = False)
compras = data.Buy[data.Buy == True].count()

indexes = []

for idx, row in data.iterrows():
    if row.Sell == True:
        indexes.append(idx)

for i in data.index:
    if data.Buy[i] == True:
        for index in indexes:
            if (index - i) > 0:
                data.Resta[i] = index - i
                break
            else:
                pass
    else:
        data.Resta[i] = 0

rsEjex = []
rs = []

for i in range(len(data)):
    if data.loc[i, "Resta"] > 0:
        for a in range(2, data.loc[i, "Resta"] + 1):
            rsEjex.append(a)
            rendimiento = (data.loc[(i + a), "AdjClose"]/data.loc[i, "AdjClose"] - 1) * 100
            rs.append(rendimiento)

df = pd.DataFrame(list(zip(rsEjex, rs)), columns = ["Ruedas", "Rendimientos"])
rendmean = df.Rendimientos.groupby(df.Ruedas).mean().to_frame()
rendcount = df.Rendimientos.groupby(df.Ruedas).count().to_frame()
rendcount.columns = ["Observaciones"]
rendcount["Concrecion"] = rendcount.Observaciones/compras 
rendtotal = pd.concat([rendmean, rendcount], axis = 1)
rendtotal["Ratio"] = rendtotal.Rendimientos * rendtotal.Concrecion
rendtotal = rendtotal[rendtotal.index < 101]

fig, ax = plt.subplots(figsize = (15, 7), nrows = 2)
ax[0].plot(rendtotal.index, rendtotal.Rendimientos, color = "black", ls = "solid", label = "Rendimiento Medio")
ax[0].axhline(y = 10, color = "red", ls = "dashed")
ax[0].set_ylabel("Rendimiento porcentual", fontsize = 14)
ax[0].legend(loc = "upper left")
ax2 = ax[0].twinx()
ax2.bar(rendtotal.index, rendtotal.Concrecion, color = "gray", alpha = 0.5, width = 0.6, ec = "white", 
        label = "Observaciones sobre total de señales de compra")
ax2.set_ylabel("Proporción", fontsize = 14)
ax2.legend(bbox_to_anchor = (0.5, 1))
ax[1].plot(rendtotal.index, rendtotal.Ratio, ls = "solid", color = "green", lw = 2, label = "Rendimiento Asegurado")
ax[1].set_xlabel("Cantidad de ruedas posterior al cruce de medias", fontsize = 14)
ax[1].set_ylabel("Rendimiento x Proporción", fontsize = 14)
ax[1].legend(loc = "upper left")
fig.suptitle("Rendimientos luego de cruce entre EMA de " + str(fast) + " ruedas y EMA de " + str(slow) + " ruedas antes de cruce de venta",
             y = 0.96, fontsize = 15)
plt.subplots_adjust(hspace = 0)
ax[0].set_zorder(1)
ax[0].patch.set_visible(False)
ax[0].get_xaxis().set_visible(False)
plt.show() 
