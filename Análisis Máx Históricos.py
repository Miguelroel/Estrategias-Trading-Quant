# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 19:19:38 2021

@author: G&L
"""

import numpy as np
import matplotlib.pyplot as plt
from pandas_datareader import data as pdr
import datetime as dt
import pandas as pd

#Definimos las fechas de comienzo y final de nuestras series históricas
end_date = dt.date.today()
start_date = "2000-01-01"

#Definimos una función para traer la data de un ticker con Yahoo Finance, utilizando el módulo pandas_datareader
def getDailyAdj(symbol):
    #Pasamos como argumentos nuestras variables que contienen las fechas
    data = pdr.get_data_yahoo(symbol, start_date, end_date)
    #Nos quedamos solo con estas columnas
    data = data.filter(items = ["Open", "High", "Low", "Adj Close", "Volume"], axis = 1)
    return data

#Definimos la lista de nuestros tickers a analizar
tickers = ["AAPL", "AMZN", "NFLX", "MELI", "FB"]

#Creamos nuestra figura donde vamos a plasmar nuestro gráfico
fig, ax = plt.subplots(figsize = (12, 7))

#Iteramos sobre cada uno de los tickers para hacer nuestro análisis
for ticker in tickers:
    #Obtenemos la data histórica
    data = getDailyAdj(ticker)
    #Calculamos los máximos acumulados
    data["max"] = data["Adj Close"].cummax()
    #Dejamos en 0 todos los registros en donde no se regitró un nuevo máximo histórico
    data["max_v2"] = np.where(data["max"] != data["max"].shift(), data["max"], 0)
    #Nos quedamos solo con los máximos que fueron seguidos de dos velas rojas, y dejamos en 0 el resto
    data["max_historico"] = np.where((data["max_v2"] != 0) & (data["Adj Close"].shift(-1) < data["Adj Close"]) & 
                                 (data["Adj Close"].shift(-2) < data["Adj Close"].shift(-1)), data["max_v2"], 0)
    data = data.dropna()
    #Creamos estas listas para almacenar la cantidad de ruedas posterior al ATH y los rendimientos medios en cada cantidad
    rsEjex = []
    rsmean = []
    #Iteramos sobre la cantidad de ruedas posterior al ATH (de 2 a 100)
    for i in range(2, 101):
        rsEjex.append(i)
        data_v2 = data
        #Calculamos el rendimiento para i ruedas posterior al ATH
        data_v2["Rend"] = np.where(data_v2["max_historico"] > 0, (data_v2["Adj Close"].shift(-i) / data_v2["Adj Close"] - 1) * 100, 0)
        data_v2 = data_v2[data_v2["max_historico"] > 0]
        #Calculamos el rendimiento medio entre todos los ATH y agregamos el resultado a la lista rsmean
        rsmean.append(data_v2["Rend"].mean())
    #Creamos un dataframe con las dos listas anteriores para poder realizar algunos análisis
    df = pd.DataFrame(list(zip(rsEjex, rsmean)), columns = ["Ruedas", "Rendimiento"])
    #Creamos una columna donde nos pone un 1 cuando el rendimiento promedio deja de ser 0 
    df["Cruce"] = np.where((df["Rendimiento"] > 0) & (df["Rendimiento"].shift() <= 0), 1, 0)
    df = df[df["Cruce"] == 1]
    #Nos quedamos solo con el primer valor, ya que nos interesa saber cuándo el activo se recupera por primera vez
    ruedas = df["Ruedas"].to_list()[0]
    #Graficamos en nuestra figura el rendimiento medio como función de la cantidad de ruedas posterior al ATH correspondiente a este activo
    ax.plot(rsEjex, rsmean, lw = 2, label = ticker)
    #Escribimos cuántas ruedas, en promedio, tarda este activo en recuperarse luego de un ATH seguido de dos velas rojas
    print(f"{ticker} recupera sus niveles de ATH luego de: {ruedas} ruedas")

#Graficamos la línea de referencia en 0 en nuestra figura
ax.axhline(y = 0, color = "red", ls = "dashed")
#Terminamos de detallar nuestro gráfico
ax.set_ylabel("Rendimiento porcentual medio", fontsize = 14)
ax.set_xlabel("Cantidad de ruedas posterior al máximo histórico", fontsize = 14)
fig.suptitle("Rendimientos desde máximos históricos seguidos de dos velas rojas", y = 0.95, fontsize = 16)
plt.legend( loc = "upper left")
plt.show()