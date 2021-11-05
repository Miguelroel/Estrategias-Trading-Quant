# -*- coding: utf-8 -*-
"""
Created on Sat Oct  9 18:32:45 2021

@author: G&L
"""

import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from math import floor

TOKEN = "DS0RGXA4B93RVQTG"

def get_historical_data(symbol):
    function = "TIME_SERIES_DAILY_ADJUSTED"
    url = "https://www.alphavantage.co/query"
    parametros = {"function": function, "symbol": symbol, "outputsize": "full", "apikey": TOKEN}
    
    r = requests.get(url, params = parametros)
    js = r.json()["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(js, orient = "index")
    df = df.astype("float")
    df = df.round(2)
    df.index.name = "Date"
    df = df.sort_values(by = "Date", ascending = True)
    df.index = pd.to_datetime(df.index)
    df = df.drop(["4. close", "7. dividend amount", "8. split coefficient"], axis = 1)
    df.columns = ["open", "high", "low", "close", "volume"]
    return df

meli = get_historical_data("MELI")

def get_bbands(data, lookback):
    std = data.rolling(lookback).std()
    middle_bb = data.ewm(span = lookback).mean()
    upper_bb = middle_bb + 2*std
    lower_bb = middle_bb - 2*std
    return middle_bb, upper_bb, lower_bb

meli["middle_bb"], meli["upper_bb"], meli["lower_bb"] = get_bbands(meli["close"], 20)
meli = meli.dropna()

def get_rsi(close, lookback):
    ret = close.diff()
    up = []
    down = []
    
    for i in range(len(ret)):
        if ret[i] < 0:
            up.append(0)
            down.append(ret[i])
        else:
            up.append(ret[i])
            down.append(0)
            
    up_series = pd.Series(up)
    down_series = pd.Series(down).abs()
    
    up_ewm = up_series.ewm(span = lookback).mean()
    down_ewm = down_series.ewm(span = lookback).mean()
    
    rs = up_ewm/down_ewm
    rsi = 100 - (100 / (1 + rs))
    rsi_df = pd.DataFrame(rsi).rename(columns = {0: "rsi"}).set_index(close.index)
    return rsi_df

meli["rsi_14"] = get_rsi(meli["close"], 14)
meli = meli.dropna()
meli = meli.round(2)

def implement_bbands_rsi_strategy(prices, lower_bb, upper_bb, rsi):
    buy_price = []
    sell_price = []
    bbands_rsi_signal = []
    signal = 0
    
    for i in range(len(prices)):
        if prices[i] < lower_bb[i] and prices[i-1] > lower_bb[i-1] and rsi[i] < 30:
            if signal != 1:
                buy_price.append(prices[i])
                sell_price.append(np.nan)
                signal = 1
                bbands_rsi_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                bbands_rsi_signal.append(0)
                
        elif prices[i] > upper_bb[i] and prices[i-1] < upper_bb[i-1] and rsi[i] > 70:
            if signal != -1 and signal != 0:
                buy_price.append(np.nan)
                sell_price.append(prices[i])
                signal = -1
                bbands_rsi_signal.append(signal)
            else:
                buy_price.append(np.nan)
                sell_price.append(np.nan)
                bbands_rsi_signal.append(0)
        
        else:
            buy_price.append(np.nan)
            sell_price.append(np.nan)
            bbands_rsi_signal.append(0)
            
    return buy_price, sell_price, bbands_rsi_signal

buy_price, sell_price, bbands_rsi_signal = implement_bbands_rsi_strategy(meli["close"], meli["lower_bb"],
                                                                         meli["upper_bb"], meli["rsi_14"])

position = []
for i in range(len(bbands_rsi_signal)):
    if bbands_rsi_signal[i] > 1:
        position.append(1)
    else:
        position.append(0)

for i in range(len(meli["close"])):
    if bbands_rsi_signal[i] == 1:
        position[i] = 1
    elif bbands_rsi_signal == -1:
        position[i] = 0
    else:
        position[i] = position[i-1]
        
close_price = meli["close"]
lower_bb = meli["lower_bb"]
middle_bb = meli["middle_bb"]
upper_bb = meli["upper_bb"]
rsi = meli["rsi_14"]
bbands_rsi_signal_df = pd.DataFrame(bbands_rsi_signal).rename(columns = {0: "signal"}).set_index(meli.index)
bbands_rsi_position_df = pd.DataFrame(position).rename(columns = {0: "position"}).set_index(meli.index)

frames = [close_price, lower_bb, middle_bb, upper_bb, rsi, bbands_rsi_signal_df, bbands_rsi_position_df]
strategy = pd.concat(frames, axis = 1)

indexes = []
for i in range(len(strategy["signal"])):
    if strategy["signal"][i] == -1:
        indexes.append(i)
    else:
        pass
    
trade_returns = []
ruedas = []
trade_profit = []
for i in range(len(strategy["signal"])):
    if strategy["signal"][i] > 1:
        trade_returns.append(1)
        ruedas.append(1)
        trade_profit.append(1)
    else:
        trade_returns.append(0)
        ruedas.append(0)
        trade_profit.append(0)
        
for i in range(len(strategy["signal"])):
    if strategy["signal"][i] == 1:
        for index in indexes:
            if (index - i) > 0:
                returns = (strategy["close"][index]/strategy["close"][i] - 1) * 100
                investment_value = 10000
                number_of_stocks = floor(investment_value/strategy["close"][i])
                profit = (strategy["close"][index] - strategy["close"][i]) * number_of_stocks
                trade_returns[i] = returns
                ruedas[i] = index - i
                trade_profit[i] = profit
                break
            else:
                pass
    else:
        trade_returns[i] = 0
        ruedas[i] = 0
        trade_profit[i] = 0

trade_returns_df = pd.DataFrame(trade_returns).rename(columns = {0: "trade_returns"}).set_index(strategy.index)
ruedas_df = pd.DataFrame(ruedas).rename(columns = {0: "ruedas"}).set_index(strategy.index)
trade_profit_df = pd.DataFrame(trade_profit).rename(columns = {0: "trade_profit"}).set_index(strategy.index)
trade_returns_df = trade_returns_df[trade_returns_df["trade_returns"] != 0]
ruedas_df = ruedas_df[ruedas_df["ruedas"] != 0]
trade_profit_df = trade_profit_df[trade_profit_df["trade_profit"] != 0]
avg_trade_ret = round(trade_returns_df["trade_returns"].mean(), 2)
median_trade_ret = round(trade_returns_df["trade_returns"].median(), 2)
min_trade_ret = round(trade_returns_df["trade_returns"].min(), 2)
max_trade_ret = round(trade_returns_df["trade_returns"].max(), 2)
cant_trades = trade_returns_df["trade_returns"].count()
avg_duracion = round(ruedas_df["ruedas"].mean(), 2)
trade_returns_pos = trade_returns_df[trade_returns_df["trade_returns"] > 0]
pct_trade_pos = round((trade_returns_pos["trade_returns"].count()/trade_returns_df["trade_returns"].count()) * 100, 2)
trade_returns_neg = trade_returns_df[trade_returns_df["trade_returns"] < 0]
pct_trade_neg = round((trade_returns_neg["trade_returns"].count()/trade_returns_df["trade_returns"].count()) * 100, 2)
trade_profit_pos = trade_profit_df[trade_profit_df["trade_profit"] > 0]
trade_profit_neg = trade_profit_df[trade_profit_df["trade_profit"] < 0]
gross_profit_pos = round(sum(trade_profit_pos["trade_profit"]), 2)
gross_profit_neg = round(sum(trade_profit_neg["trade_profit"]), 2)
factor = round(abs(gross_profit_pos/gross_profit_neg), 2)

print(f"Average trade return: {avg_trade_ret}%", f"\nMedian trade return: {median_trade_ret}%",
      f"\nMinimum trade return: {min_trade_ret}%", f"\nMaximum trade return: {max_trade_ret}%",
      f"\nCantidad de trades: {cant_trades}", f"\nDuración promedio del trade: {avg_duracion}",
      f"\nPorcentaje de trades positivos: {pct_trade_pos}%", f"\nPorcentaje de trades negativos: {pct_trade_neg}%",
      f"\nTotal gross profit inviertiendo 10k USD en cada trade: ${gross_profit_pos}",
      f"\nTotal gross loss invirtiendo 10k USD en cada trade: ${gross_profit_neg}", f"\nProfit factor: {factor}")



