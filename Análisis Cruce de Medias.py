# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 20:16:34 2021

@author: G&L
"""

import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt
from pandas_datareader import data as pdr

#Definimos los parámetros que van a afectar nuestro análisis y los almacenamos en variables
start_date = "2008-01-01"
end_date = dt.date.today()
symbol = "MELI"
fastema = 5
slowema = 20

#Definimos una función para calcular cualquier EMA (Exponential Moving Average) que queramos
def get_ema(close, lookback):
    ema = close.ewm(span = lookback).mean()
    return ema

#Definimos una función que nos devuelve el dataframe del ticker deseado con las columnas de las EMAs rápida y lenta
def tabla():
    #Traemos la data de Yahoo Finance usando la librería pandas_datareader
    data = pdr.get_data_yahoo(symbol, start_date, end_date)
    #Calculamos las columnas con las EMAs
    data["EMA " + str(fastema)] = get_ema(data["Adj Close"], fastema)
    data["EMA " + str(slowema)] = get_ema(data["Adj Close"], slowema)
    data = data.dropna()
    return data

#Traemos nuestra data llamando a la función tabla
data = tabla()
#Creamos una columna en el dataframe con nuestra señal de compra
data["Buy"] = (data["EMA " + str(fastema)] > data["EMA " + str(slowema)]) & (data["EMA " + str(fastema)].shift() < data["EMA " + str(slowema)].shift())
#Creamos una columna en el dataframe con nuestra señal de venta
data["Sell"] = (data["EMA " + str(fastema)] < data["EMA " + str(slowema)]) & (data["EMA " + str(fastema)].shift() > data["EMA " + str(slowema)].shift())
#Esta columna la creamos para almacenar la cantidad de días que mantuvimos el activo según nuestra señal de compra y venta
data["Posicion_Dias"] = 0
#Reseteamos el índice del dataframe para que nos quede de 0 a n
data = data.reset_index(drop = False)
#Obtenemos el valor histórico de la cantidad de órdenes de compra que nos dio nuestra señal
compras = data["Buy"][data["Buy"] == True].count()

indexes = []

#Iteramos sobre el dataframe, obtenemos el índice de los registros en donde hubo una señal de venta y los almacenamos en la lista indexes
for i in range(len(data)):
    if data.loc[i, "Sell"] == True:
        indexes.append(i)

#Iteramos sobre el dataframe y preguntamos si hubo una señal de compra en cada registro
for i in range(len(data)):
    if data.loc[i, "Buy"] == True:
        #Iteramos sobre los índices de venta, para encontrar el primero que vino después de la señal de compra en el eje del tiempo
        for index in indexes:
            if (index - i) > 0:
                #Le asignamos a la columna Posicion_Dias el valor de la resta entre los índices de venta y compra, que simboliza la cantidad de días que mantuvimos el activo en cartera
                data.loc[i, "Posicion_Dias"] = index - i
                #Rompemos el for loop sobre indexes
                break
            else:
                pass
    #Si no hubo señal de compra, simplemente dejamos en 0 la columna Posicion_Dias
    else:
        data.loc[i, "Posicion_Dias"] = 0


rsEjex = []
rs = []

#Iteramos sobre el dataframe y preguntamos si hubo señal de compra
for i in range(len(data)):
    if data.loc[i, "Posicion_Dias"] > 0:
        #Si la hubo, iteramos sobre cada uno de los días que mantuvimos el activo y calculamos el rendimiento para cada uno de ellos
        for a in range(2, data.loc[i, "Posicion_Dias"] + 1):
            #Agregamos la cantidad de días a la lista rsEjex
            rsEjex.append(a)
            rendimiento = (data.loc[(i + a), "Adj Close"]/data.loc[i, "Adj Close"] - 1) * 100
            #Agregamos el rendimiento a la lista rs
            rs.append(rendimiento)

#Creamos un dataframe combinando las dos listas creadas anteriormente
df = pd.DataFrame(list(zip(rsEjex, rs)), columns = ["Ruedas", "Rendimientos"])
#Calculamos el rendimiento medio por cantidad de ruedas que mantuvimos el activo
rendmean = df["Rendimientos"].groupby(df["Ruedas"]).mean().to_frame()
#Calculamos la cantidad de veces que mantuvimos el activo por rueda
rendcount = df["Rendimientos"].groupby(df["Ruedas"]).count().to_frame()
rendcount.columns = ["Observaciones"]
#Calculamos el porcentaje de veces que mantuvimos el activo por rueda sobre el total de señales de compra en el dataframe
rendcount["Concreción"] = rendcount["Observaciones"]/compras 
#Concatenamos ambas tablas
rendtotal = pd.concat([rendmean, rendcount], axis = 1)
#Calculamos el rendimiento asegurado por rueda multiplicando el rendimiento medio por el porcentaje de concreción
rendtotal["Ratio"] = rendtotal["Rendimientos"] * rendtotal["Concreción"]
#Definimos el límite de ruedas en 100
rendtotal = rendtotal[rendtotal.index < 101]

#Creamos nuestra figura
fig, ax = plt.subplots(figsize = (12, 7), nrows = 2)
#Graficamos rendimiento medio por rueda
ax[0].plot(rendtotal.index, rendtotal["Rendimientos"], color = "black", ls = "solid", label = "Rendimiento Medio")
ax[0].axhline(y = 10, color = "red", ls = "dashed")
ax[0].set_ylabel("Rendimiento porcentual", fontsize = 14)
ax[0].legend(loc = "upper left")
#Graficamos porcentaje de concreción por rueda en el eje derecho del primer gráfico
ax2 = ax[0].twinx()
ax2.bar(rendtotal.index, rendtotal["Concreción"], color = "gray", alpha = 0.5, width = 0.6, ec = "white", 
        label = "Observaciones sobre total de señales de compra")
ax2.set_ylabel("Proporción", fontsize = 14)
ax2.legend(bbox_to_anchor = (0.65, 1))
#Graficamos rendimiento asegurado en el segundo gráfico
ax[1].plot(rendtotal.index, rendtotal["Ratio"], ls = "solid", color = "green", lw = 2, label = "Rendimiento Asegurado")
ax[1].set_xlabel("Cantidad de ruedas posterior al cruce de medias", fontsize = 14)
ax[1].set_ylabel("Rendimiento x Proporción", fontsize = 14)
ax[1].legend(loc = "upper left")
fig.suptitle("Rendimientos luego de cruce entre EMA de " + str(fastema) + " ruedas y EMA de " + str(slowema) + " ruedas antes de señal de venta",
             y = 0.96, fontsize = 15)
plt.subplots_adjust(hspace = 0)
ax[0].set_zorder(1)
ax[0].patch.set_visible(False)
ax[0].get_xaxis().set_visible(False)
plt.show() 

#Mostramos cuál es la cantidad de ruedas óptima para mantener el activo seleccionado luego de la señal de cruce entre las EMAs seleccionadas
print("El rendimiento asegurado máximo se alcanza luego de " + str(rendtotal.index[rendtotal["Ratio"] == max(rendtotal["Ratio"])].to_list()) + 
      " ruedas, con un valor de " + str(round(max(rendtotal["Ratio"]), 2)) + "%")