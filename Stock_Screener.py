# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 19:46:05 2022

@author: migue
"""

from pandas_datareader import data as pdr
from yahoo_fin import stock_info as si
import yfinance as yf
import pandas as pd
import datetime as dt
import streamlit as st
import time
import requests
import plotly.graph_objects as go

yf.pdr_override()

#Definimos nuestro Token para poder hacer llamadas a la API de AlphaVantage
TOKEN = "DS0RGXA4B93RVQTG"

#Creamos una función para calcular EMAs (Exponential Moving Average)
def get_ema(close, lookback):
    ema = close.ewm(span = lookback).mean()
    return ema

"""
Creamos una función para calcular el Volume Indicator, un indicador que elaboré personalmente, el cual replica casi la misma fórmula utilizada para el 
cálculo del RSI pero tomando el volumen en vez del precio. Básicamente lo que intentamos medir con este indicador es si el volumen promedio de las últimas 
n ruedas está siendo alcista o bajista
"""

def get_vi(Open, Close, Volume, lookback):
    df = pd.concat([Open, Close], axis = 1)
    #Definimos una columna que nos dice si la vela del día fue positiva o negativa
    df["cuerpo"] = df["Close"]/df["Open"] - 1
    cuerpo_list = df["cuerpo"].to_list()
    vol_list = Volume.to_list()
    #Creamos dos listas para almacenar los volúmenes de los días positivos y negativos por separado
    vol_pos = []
    vol_neg = []
    
    #Agregamos el volumen del día a la lista que corresponda según la vela haya sido alcista o bajista, y agregamos 0 en caso contrario
    for i in range(len(cuerpo_list)):
        if cuerpo_list[i] < 0:
            vol_pos.append(0)
            vol_neg.append(vol_list[i])
        else:
            vol_pos.append(vol_list[i])
            vol_neg.append(0)
    
    #Transformamos las listas a series para poder aplicar algunas funciones
    vol_pos_series = pd.Series(vol_pos)
    vol_neg_series = pd.Series(vol_neg)
    
    #Le aplicamos una EMA de n períodos a las dos series obtenidas anteriormente
    vol_pos_ewm = vol_pos_series.ewm(span = lookback).mean()
    vol_neg_ewm = vol_neg_series.ewm(span = lookback).mean()
    
    #Obtenemos el índice de fuerza relativa (o Relative Strength) del volumen
    rs = vol_pos_ewm/vol_neg_ewm
    #Le aplicamos la siguiente fórmula para que nos quede un valor entre 0 y 100
    vi = 100 - (100 / (1 + rs))
    #Pasamos nuestro indicador a un dataframe de Pandas para poder incrustarlo como columna cuando queramos
    vi_df = pd.DataFrame(vi).rename(columns = {0: "VI"}).set_index(Close.index)
    return vi_df

#Hacemos nuestro primer llamado a la web para obtener la lista de todos los tickers del S&P (hacemos uso del módulo stock_info del paquete yahoo_fin)
tickers = si.tickers_sp500()
#Esta línea es necesaria porque yahoo finance usa guíones en vez de puntos para sus tickers
tickers = [item.replace(".", "-") for item in tickers]

#Nombre del ETF del S&P
index_name = "^GSPC"
#Seteamos como fecha inicial para nuestro análisis un año hacia atrás, y la fecha final en el día de hoy
start_date = dt.datetime.now() - dt.timedelta(days = 365)
end_date = dt.date.today()
#Acá creamos ya nuestro screener (obviamente solo tenemos los nombres de las columnas todavía)
exportList = pd.DataFrame(columns = ["Stock", "Price", "Volume", "VI", "RS_Rating", "50 EMA",
                                     "100 EMA", "200 EMA", "200_20 EMA", "52 Week Low", "52 Week High"])
returns_multiples = []

#Obtenemos la data del índice S&P, le calculamos el retorno acumulado hasta la fecha de hoy, y nos quedamos con dicho valor
index_df = pdr.get_data_yahoo(index_name, start_date, end_date)
index_df["Percent Change"] = index_df["Adj Close"].pct_change()
index_return = (index_df["Percent Change"] + 1).cumprod()[-1]

#Creamos un diccionario para almacenar todos los dataframes de los más de 500 tickers que componen el índice
dfs = {}

"""
Hacemos un llamado a la web por cada ticker que compone el índice, traemos el dataframe, le calculamos el retorno acumulado a la fecha de hoy, 
dividimos dicho retorno por el retorno del índice S&P (lo cual vamos a llamar a partir de ahora índice de RS -Relative Strength-)
y el resultado lo almacenamos en la lista returns_multiples, creada para dicho propósito
"""
for ticker in tickers:
    try:
        df = pdr.get_data_yahoo(ticker, start_date, end_date)
        """
        Lo que hacemos en las siguientes 4 líneas es crear la serie ajustada por dividendos y splits, 
        lo cual siempre es más conveniente a la hora de hacer cualquier tipo de análisis quant. Esta serie 
        ajustada es la que vamos a guardar como dataframe del ticker
        """
        df["factor"] = df["Adj Close"] / df["Close"]
        cols = [df["Open"] * df["factor"], df["High"] * df["factor"], df["Low"] * df["factor"], df["Adj Close"], df["Volume"]]
        df_aj = pd.concat(cols, axis = 1)
        df_aj.columns = ["Open", "High", "Low", "Close", "Volume"]
    
        #Convertimos el dataframe a diccionario y lo almacenamos en el diccionario dfs, con el correspondiente ticker como clave
        dfs[ticker] = df_aj.to_dict()
    
        df_aj["Percent Change"] = df_aj["Close"].pct_change()
        stock_return = (df_aj["Percent Change"] + 1).cumprod()[-1]
    
        returns_multiple = round(stock_return / index_return, 2)
        returns_multiples.extend([returns_multiple])
    
        #Esta línea la ponemos para evitar errores, ya que son muchos llamados a la web
        time.sleep(0.1)
    
    except:
        pass

#Nos armamos un dataframe con todos los tickers listados y sus correspondientes índices de RS
rs_df = pd.DataFrame(list(zip(tickers, returns_multiples)), columns = ["Ticker", "Return Multiple"])
#Creamos esta columna para listar de mayor a menor los índices de RS
rs_df["RS_Rating"] = rs_df["Return Multiple"].rank(pct = True) * 100
#Y acá nos quedamos con el 30% que mayor fuerza relativa tiene con respecto al mercado
rs_df = rs_df[rs_df["RS_Rating"] >= rs_df["RS_Rating"].quantile(0.7)]

"""
Tomamos los tickers que cumplen la condición anterior y vamos a iterar por cada uno de ellos, 
vamos a preguntar si cumplen una cierta cantidad de condiciones y, en caso de cumplirlas, vamos a 
almacenar a dicho activo en nuestro dataframe exportList; es decir, en nuestro screener final
"""
rs_stocks = rs_df["Ticker"].to_list()
for stock in rs_stocks:
    try:
        #Volvemos a traer el dataframe que habíamos almacenado como diccionario en dfs
        df = pd.DataFrame(dfs[stock])
        #Llamamos a la función que nos crea el indicador VI
        df["VI"] = get_vi(df["Open"], df["Close"], df["Volume"], 20)
        #Definimos 3 períodos de EMA y calculamos una columna por cada período
        ema = [50, 100, 200]
        for x in ema:
            df["EMA " + str(x)] = get_ema(df["Close"], x)
        
        #Estos son los datos que vamos a testear vs. ciertos parámetros para verificar que el ticker cumple con las condiciones
        currentClose = df["Close"][-1]
        currentVolume = df["Volume"][-1]
        current_vi = df["VI"][-1]
        ema_50 = df["EMA 50"][-1]
        ema_100 = df["EMA 100"][-1]
        ema_200 = df["EMA 200"][-1]
        #El mínimo del último año
        low_of_52_week = min(df["Low"][-260:])
        #El máximo del último año
        high_of_52_week = max(df["High"][-260:])
        RS_Rating = rs_df[rs_df["Ticker"] == stock]["RS_Rating"].to_list()[0]
        
        #EMA de 200 de un mes hacia atrás
        try:
            ema_200_20 = df["EMA 200"][-20]
        except Exception:
            ema_200_20 = 0
        
        #Estas son nuestras condiciones
        condition1 = ema_50 > ema_100 > ema_200
        condition2 = currentClose > ema_50
        #Esto es para verificar que la EMA de 200 esté en tendencia alcista
        condition3 = ema_200 > ema_200_20
        condition4 = currentClose >= (1.3 * low_of_52_week)
        condition5 = currentClose >= (0.75 * high_of_52_week)
        condition6 = current_vi >= 70
        
        #Preguntamos si se cumplen todas las condiciones y, en caso de ser así, anexamos la info del ticker a nuestro screener
        if (condition1 and condition2 and condition3 and condition4 and condition5 and condition6):
            exportList = exportList.append({"Stock": stock, "Price": currentClose, "Volume": currentVolume, "VI": current_vi, "RS_Rating": RS_Rating,
                                            "50 EMA": ema_50, "100 EMA": ema_100, "200 EMA": ema_200, "200_20 EMA": ema_200_20, "52 Week Low": low_of_52_week,
                                            "52 Week High": high_of_52_week}, ignore_index = True)
            
    except Exception:
        print(f"Could not gather data on {stock}")
        

#Ordenamos nuestro screener según el ranking de RS y listo
exportList = exportList.sort_values(by = "RS_Rating", ascending = False)

"""
Ahora lo que vamos a hacer es plasmar nuestro screener en una mini APP usando el framework
streamlit y, además, le vamos a agregar el gráfico de velas diario del último año de las acciones 
que nos interesan, para corroborar que tienen un gráfico diario fuerte
"""

#Escribimos el título de nuestra página web
st.write("""
         # Stock Screener - Strongest SPY Stocks
         Listed below are the best stocks to take a long position right now, based on a strong daily chart
         """)

#Pegamos nuestro screener al inicio         
st.dataframe(exportList)

#Creamos una barra lateral para que el usuario pueda interactuar con algunos filtros
st.sidebar.header("FILTERS")

"""
Creamos un lista desplegable con las acciones que aparecen en nuestro screener, para que el 
usuario pueda seleccionar la que quiera y, de esa forma, filtrar el gráfico de velas. Guardamos 
la elección en una variable
"""
symbol = st.sidebar.selectbox("Please choose a stock from the list", exportList["Stock"].to_list())

#Creamos una función para que nos traiga el nombre de la compañía del ticker que seleccionamos
def get_name(simbolo):
    function = "OVERVIEW"
    url = "https://www.alphavantage.co/query"
    parametros = {"function": function, "symbol": simbolo, "apikey": TOKEN}
    r = requests.get(url, params = parametros)
    js = r.json()
    company_name = js["Name"]
    return company_name

#Hacemos el llamado a la función y guardamos el nombre de la compañía en una variable
company_name = get_name(symbol)

#Traemos el dataframe del ticker seleccionado del diccionario dfs    
data = pd.DataFrame(dfs[symbol])
#Seleccionamos solo las columnas OHLC y la fecha
data = data.filter(items = ["Open", "High", "Low", "Close"], axis = 1)
data = data.reset_index(drop = False).rename(columns = {"index": "Date"})
data["Date"] = pd.to_datetime(data["Date"])

#Creamos un encabezado en la APP para presentar el gráfico
st.header(f"Daily chart - Last 365 days\n**{company_name}**")

#Creamos el objeto fig con el gráfico de velas, utilizando la librería plotly
candlestick = go.Candlestick(x = data["Date"], open = data["Open"], high = data["High"], low = data["Low"], close = data["Close"], name = symbol)
fig = go.Figure(data = [candlestick])
#Esta línea es para omitir los fines de semana en nuestro gráfico de velas (ya que son días sin data)
fig.update_xaxes(type = "category")
fig.update_layout(height = 600)

#Pegamos el gráfico en nuestra APP
st.plotly_chart(fig, use_container_width = True)
