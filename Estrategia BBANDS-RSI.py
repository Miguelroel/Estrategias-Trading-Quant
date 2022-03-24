import pandas as pd
from math import floor
from pandas_datareader import data as pdr
import datetime as dt

#Elgimos y guardamos en variables el activo y el período de fechas que queremos analizar. El activo y la fecha de inicio los elige el usuario
symbol = input("Seleccione un activo para analizar: ").upper()
start_date = input("Seleccione la fecha de inicio del análisis: ")
end_date = dt.date.today()

#Definimos una función que nos trae la data histórica del activo seleccionado para las fechas seleccionadas
def get_historical_data():
    data = pdr.get_data_yahoo(symbol, start_date, end_date)
    #Nos quedamos solo con estas columnas
    data = data.filter(items = ["High", "Low", "Open", "Adj Close", "Volume"], axis = 1)
    return data

#Llamamos a la función y guardamos el resultado en la variable data
data = get_historical_data()

#Definimos una función que nos calcula el indicador técnico Bollinger Bands (Bandas de Bollinger), pasándole como argumentos los precios de cierre y el número de períodos para hacer el cálculo
def get_bbands(close, lookback):
    #Calculamos el desvío estándar de la serie de precios, tomando el número de períodos pasado como argumento
    std = close.rolling(lookback).std()
    #Calculamos la media exponencial de la serie de precios, tomando el número de períodos pasado como argumento (esta va a ser la línea del medio del indicador)
    middle_bb = close.ewm(span = lookback).mean()
    #Calculamos la línea superior del indicador
    upper_bb = middle_bb + 2 * std
    #Calculamos la línea inferior del indicador
    lower_bb = middle_bb - 2 * std
    return middle_bb, upper_bb, lower_bb

#Creamos las columnas en nuestro dataframe con el indicador BBANDS, llamando a la función creada anteriormente
data["middle_bb"], data["upper_bb"], data["lower_bb"] = get_bbands(data["Adj Close"], 20)
data = data.dropna()

#Creamos una función para calcular el indicador técnico RSI (Relative Strength Index), también pasando como argumentos los precios de cierre y la cantidad de períodos deseada
def get_rsi(close, lookback):
    #Calculamos los cambios absolutos diarios de los precios
    ret = close.diff()
    up = []
    down = []
    
    #Iteramos sobre los cambios absolutos y preguntamos si fueron positivos o negativos
    for i in range(len(ret)):
        if ret[i] < 0:
            #Si fue negativo agregamos el cambio a la lista down, y un 0 a la lista up
            up.append(0)
            down.append(ret[i])
        else:
            #Si fue positivo agregamos el cambio a la lista up, y un 0 a la lista down
            up.append(ret[i])
            down.append(0)
    
    #Convertimos las listas en series para poder hacer otros cálculos        
    up_series = pd.Series(up)
    #Nos quedamos con los cambios absolutos acá
    down_series = pd.Series(down).abs()
    
    #Le aplicamos una media exponencial a las series, tomando como período el argumento pasado a la función
    up_ewm = up_series.ewm(span = lookback).mean()
    down_ewm = down_series.ewm(span = lookback).mean()
    
    #Calculamos el índice rs dividiendo la serie con la EMA de los cambios positivos sobre la serie con la EMA de los cambios negativos
    rs = up_ewm / down_ewm
    #Le aplicamos la siguiente fórmula para que el índice quede entre 0 y 100
    rsi = 100 - (100 / (1 + rs))
    #Convertimos la serie a un dataframe para poder insertarlo como columna, y le aplicamos el mismo índice que la serie con los precios
    rsi_df = pd.DataFrame(rsi).rename(columns = {0: "RSI"}).set_index(close.index)
    return rsi_df

#Calculamos la columna del RSI en nuestro dataframe llamando a la función creada para el indicador
data["RSI"] = get_rsi(data["Adj Close"], 14)
#Eliminamos los nulls de nuestro dataframe y redondeamos todo a dos decimales
data = data.dropna()
data = data.round(2)


#Definimos una función para calcular nuestra señal de compra, pasando como argumentos la serie de precios de cierre, las columnas que contienen las bandas inferior y superior del indicador BBANDS y la serie del RSI
def implement_bbands_rsi_strategy(prices, lower_bb, upper_bb, rsi):
    bbands_rsi_signal = []
    signal = 0
    
    #Iteramos sobre la serie de precios y preguntamos si se cumplen las condiciones de compra o venta
    for i in range(len(prices)):
        #Esta es la condición de compra
        if prices[i] < lower_bb[i] and prices[i-1] > lower_bb[i-1] and rsi[i] < 30:
            #Si no estamos comprados (signal es distinto de 1) la signal se convierte en 1 y agregamos su valor a la lista bbands_rsi_signal
            if signal != 1:
                signal = 1
                bbands_rsi_signal.append(signal)
            #Si ya estamos comprados no vamos a comprar de nuevo, por lo que le agregamos un cero a nuestra lista de señales
            else:
                bbands_rsi_signal.append(0)
                
        #Esta es la señal de venta
        elif prices[i] > upper_bb[i] and prices[i-1] < upper_bb[i-1] and rsi[i] > 70:
            #Si estamos comprados (signal es igual a 1) la signal se convierte en -1 (pasamos a estar vendidos) y agregamos su valor en la lista bbands_rsi_signal
            if signal != -1 and signal != 0:
                signal = -1
                bbands_rsi_signal.append(signal)
            #Si no estamos comprados (si la signal es -1 o 0) no tenemos nada que vender, por lo que agregamos un 0 en nuestra lista de señales
            else:
                bbands_rsi_signal.append(0)
        
        #Si no tenemos señal de venta ni de compra, simplemente agregamos un 0 en nuestra lista de señales
        else:
            bbands_rsi_signal.append(0)
            
    #Devolvemos la lista de señales
    return bbands_rsi_signal

#Llamamos a la función de señales y guardamos el resultado en la variable bbands_rsi_signal
bbands_rsi_signal = implement_bbands_rsi_strategy(data["Adj Close"], data["lower_bb"],
                                                                         data["upper_bb"], data["RSI"])

#A continuación, vamos a calcular nuestra posición
position = []
#Este for loop es necesario para que la lista position tenga la misma cantidad de elemnos que la lista bbands_rsi_signal
for i in range(len(bbands_rsi_signal)):
    if bbands_rsi_signal[i] > 1:
        position.append(1)
    else:
        position.append(0)

#Iteramos sobre nuestra lista de señales y preguntamos si hubo una señal de compra o venta
for i in range(len(bbands_rsi_signal)):
    #Si hubo una señal de compra, agregamos un 1 a la lista que contiene nuestra posición, simbolizando que estamos comprados en el activo
    if bbands_rsi_signal[i] == 1:
        position[i] = 1
    #Si hubo una señal de venta, agregamos un 0 a la lista position, simbolizando que ya no estamos comprados en el activo
    elif bbands_rsi_signal == -1:
        position[i] = 0
    #Si no hubo señal de compra ni de venta, no cambiamos nuestra posición y la mantenemos igual que en la rueda anterior
    else:
        position[i] = position[i-1]

#Obtenemos todos estos dataframes por separado para poder juntarlos luego en uno solo        
close_price = data["Adj Close"]
lower_bb = data["lower_bb"]
middle_bb = data["middle_bb"]
upper_bb = data["upper_bb"]
rsi = data["RSI"]
#Convertimos a dataframe las listas de señales y de posición, pasándoles como índice las fechas de nuestro dataframe con los precios
bbands_rsi_signal_df = pd.DataFrame(bbands_rsi_signal).rename(columns = {0: "Signal"}).set_index(data.index)
bbands_rsi_position_df = pd.DataFrame(position).rename(columns = {0: "Position"}).set_index(data.index)

frames = [close_price, lower_bb, middle_bb, upper_bb, rsi, bbands_rsi_signal_df, bbands_rsi_position_df]
#Armamos nuestro dataframe final con la data histórcia de precios + los indicadores técnicos + las columnas de señales de compra/venta y posición en el activo
strategy = pd.concat(frames, axis = 1)

indexes = []
#Iteramos sobre el dataframe y preguntamos si hubo una señal de venta
for i in range(len(strategy["Signal"])):
    #Si la hubo, agregamos el número de orden del registro en la lista indexes
    if strategy["Signal"][i] == -1:
        indexes.append(i)
    else:
        pass
    
trade_returns = []
ruedas = []
trade_profit = []
#Este for loop es necesario para que las tres listas que creamos en el paso anterior tengan el mismo tamaño que nuestro dataframe strategy
for i in range(len(strategy["Signal"])):
    if strategy["Signal"][i] > 1:
        trade_returns.append(1)
        ruedas.append(1)
        trade_profit.append(1)
    else:
        trade_returns.append(0)
        ruedas.append(0)
        trade_profit.append(0)

#Iteramos sobre el dataframe strategy y preguntamos si hubo una señal de compra        
for i in range(len(strategy["Signal"])):
    #En el caso de que haya habido una señal de compra, iteramos sobre la lista indexes para encontrar la señal de venta más cercana luego de nuestra señal de compra
    if strategy["Signal"][i] == 1:
        for index in indexes:
            if (index - i) > 0:
                #En caso de haberla encontrado, calculamos el rendimiento del trade
                returns = (strategy["Adj Close"][index] / strategy["Adj Close"][i] - 1) * 100
                #Hacemos de cuenta que la cantidad de dinero que invertimos en cada trade es 10000 USD
                investment_value = 10000
                #Calculamos el número de acciones que compramos con los 10000 USD
                number_of_stocks = floor(investment_value / strategy["Adj Close"][i])
                #Calculamos la ganancia monetaria del trade
                profit = (strategy["Adj Close"][index] - strategy["Adj Close"][i]) * number_of_stocks
                #Agregamos el rendimiento, la ganancia monetaria y la cantidad de ruedas que duró el trade a sus correspondientes listas
                trade_returns[i] = returns
                ruedas[i] = index - i
                trade_profit[i] = profit
                #Rompemos el for loop sobre la lista indexes
                break
            else:
                pass
    #Si no hubo una señal de compra, simplemente agregamos un 0 a las listas de rendimiento, ganancia y cantidad de ruedas del trade
    else:
        trade_returns[i] = 0
        ruedas[i] = 0
        trade_profit[i] = 0

"""
A continuación, vamos a calcular las métricas de nuestro backtesting
"""

#Convertimos a dataframe nuestras listas de rendimientos, ganancias, y cantidad de ruedas del trade. Le asignamos el mismo índice que nuestro dataframe strategy
trade_returns_df = pd.DataFrame(trade_returns).rename(columns = {0: "Trade_returns"}).set_index(strategy.index)
ruedas_df = pd.DataFrame(ruedas).rename(columns = {0: "Ruedas"}).set_index(strategy.index)
trade_profit_df = pd.DataFrame(trade_profit).rename(columns = {0: "Trade_profit"}).set_index(strategy.index)
#Nos quedamos solo con los valores distintos de 0, que son los registros en donde efectivamente hubo un trade
trade_returns_df = trade_returns_df[trade_returns_df["Trade_returns"] != 0]
ruedas_df = ruedas_df[ruedas_df["Ruedas"] != 0]
trade_profit_df = trade_profit_df[trade_profit_df["Trade_profit"] != 0]
frames = [trade_returns_df, ruedas_df, trade_profit_df]
#Concatenamos los tres dataframes para pasar a manejar uno solo
trade_metrics = pd.concat(frames, axis = 1)
#Calculamos qué decil representa cada rendimiento en nuestra distribución de datos
trade_metrics["Ranking_porcentual"] = trade_metrics["Trade_returns"].rank(pct = True, ascending = True)
#Eliminamos el 5% más alto y el 5% más bajo, ya que los podemos pensar como outliers
trade_metrics = trade_metrics[trade_metrics["Ranking_porcentual"] < 0.95]
trade_metrics = trade_metrics[trade_metrics["Ranking_porcentual"] > 0.05]
#Calculamos el rendimiento medio por trade
avg_trade_ret = round(trade_metrics["Trade_returns"].mean(), 2)
#Calculamos el rendimiento mediano de la distribución
median_trade_ret = round(trade_metrics["Trade_returns"].median(), 2)
#Claculamos el rendimiento mínimo
min_trade_ret = round(trade_metrics["Trade_returns"].min(), 2)
#Calculamos el rendimiento máximo
max_trade_ret = round(trade_metrics["Trade_returns"].max(), 2)
#Calculamos la cantidad de trades que hubo
cant_trades = trade_metrics["Trade_returns"].count()
#Calculamos la duración media por trade
avg_duracion = round(trade_metrics["Ruedas"].mean(), 2)
#Obtenemos un dataframe solo con los trades positivos
trade_pos = trade_metrics[trade_metrics["Trade_returns"] > 0]
#Calculamos el porcentaje de trades positivos, o win rate
pct_trade_pos = round((trade_pos["Trade_returns"].count() / trade_metrics["Trade_returns"].count()) * 100, 2)
#Obtenemos un dataframe solo con los trades negativos
trade_neg = trade_metrics[trade_metrics["Trade_returns"] < 0]
#Calculamos el porcentaje de trades negativos
pct_trade_neg = round((trade_neg["Trade_returns"].count() / trade_metrics["Trade_returns"].count()) * 100, 2)
#Calculamos la ganancia monetaria bruta, calculada como la suma de las ganancias de todos los trades positivos
gross_profit_pos = round(sum(trade_pos["Trade_profit"]), 2)
#Calculamos la pérdida monetaria bruta, calculada como la suma de las pérdidas de todos los trades negativos
gross_profit_neg = round(sum(trade_neg["Trade_profit"]), 2)
#Calculamos el profit factor, dividiendo la ganancia bruta sobre la pérdida bruta
factor = round(abs(gross_profit_pos / gross_profit_neg), 2)

#Imprimimos los resultados
print(f"\nAverage trade return: {avg_trade_ret}%", f"\nMedian trade return: {median_trade_ret}%",
      f"\nMinimum trade return: {min_trade_ret}%", f"\nMaximum trade return: {max_trade_ret}%",
      f"\nCantidad de trades: {cant_trades}", f"\nDuración promedio del trade: {avg_duracion} ruedas",
      f"\nPorcentaje de trades positivos: {pct_trade_pos}%", f"\nPorcentaje de trades negativos: {pct_trade_neg}%",
      f"\nTotal gross profit inviertiendo 10k USD en cada trade: ${gross_profit_pos}",
      f"\nTotal gross loss invirtiendo 10k USD en cada trade: ${gross_profit_neg}", f"\nProfit factor: {factor}")



