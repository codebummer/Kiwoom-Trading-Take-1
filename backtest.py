import sqlite3
import pandas as pd
import time, asyncio
import sys, os, json, logging
from datetime import datetime
# import matplotlib.pyplot as plt

#change the current working directory
# path = r'D:\myprojects\TradingDB' + '\\' + datetime.today().strftime('%Y-%m-%d')
path = r'D:\myprojects\TradingDB'
if not os.path.exists(path):
     os.mkdir(path)
os.chdir(path) 

tr_data = {}    
orderstatus = {} # {'stock': 'buying' or 'bought' or 'selling' or 'sold'}
with sqlite3.connect('test_tr_data.db') as file:
    query = '''SELECT name FROM sqlite_master WHERE type='table';'''
    tablenames = file.cursor().execute(query).fetchall()
    for tablename in tablenames:
        tr_data[tablename[0]] = pd.read_sql(f'SELECT * FROM [{tablename[0]}]', file)    

# break down tr_data into smaller data batches with sizes one time requests get
# simulating the real time trading environment in which data feed is incoming with a unit of those sizes
breakpoints = {}
for df_name in tr_data.keys():
    # breakpoints = [total numer, breakdown size, count, starting, ending]
    breakpoints[df_name] = [len(tr_data[df_name]), len(tr_data[df_name])/30, 0]

def breakdown(tr_data):
    global breakpoints
    for df_name, df in tr_data.items():
        tr_data[df_name] = df[breakpoints[stock][1]*breakpoints[stock][2]:breakpoints[stock][1]]
        breakpoints[stock][2] += 1
        if breakpoints[stock][1]*breakpoints[stock][2] > breakpoints[stock][0]:
            break
    return tr_data

def find_buy_sell(self, tr_data):    
    orders = {'buy':[], 'sell':[]}
    buy_conditions = {}
    sell_conditions = {}
    stocks = []
    # initial formatting in the first layer for dictionaries , buy_conditions and sell_conditions
    for df_name in tr_data.keys():
        stock = df_name.split('_')[0]
        stocks.append(stock)
        buy_conditions[stock] = {}
        sell_conditions[stock] = {}

    # initial formatting in the second layer for dictionaries , buy_conditions and sell_conditions        
    for stock in stocks:
        for condition in ['MA', 'Bollinger']:
            buy_conditions[stock][condition] = True
            sell_conditions[stock][condition] = True
            
    for df_name in tr_data.keys():
        if '월봉' in df_name or '주봉' in df_name or '일봉' in df_name or '60분' in df_name or '30분' in df_name or '10분' in df_name or '3분' in df_name:
            for idx in range(-60, 0):
                if tr_data[df_name]['MA60'].values[idx] < tr_data[df_name]['MA20'].values[idx] < tr_data[df_name]['MA10'].values[idx] < tr_data[df_name]['MA5'].values[idx] < tr_data[df_name]['MA3'].values[idx]:
                    stock = tr_data[df_name].split('_')[0]
                    buy_conditions[stock]['MA'] = buy_conditions[stock]['MA'] and True
                    sell_conditions[stock]['MA'] = False
                else:
                    stock = tr_data[df_name].split('_')[0]                        
                    buy_conditions[stock]['MA'] = False
                    sell_conditions[stock]['MA'] = sell_conditions[stock]['MA'] and True
        if '60분' in df_name or '30분' in df_name or '10분' in df_name or '5분' in df_name or '3분' in df_name or '1분' in df_name:                
            if tr_data[df_name]['PB'].values[-1] < 0.2 and tr_data[df_name]['SQZ'].values[-1] < 10:
                stock = tr_data[df_name].split('_')[0]
                buy_conditions[stock]['Bollinger'] = buy_conditions[stock]['Bollinger'] and True
                sell_conditions[stock]['Bollinger'] = False
            elif tr_data[df_name]['PB'].values[-1] > 0.8:
                stock = tr_data[df_name].split('_')[0]
                buy_conditions[stock]['Bollinger'] = False
                sell_conditions[stock]['Bollinger'] = sell_conditions[stock]['Bollinger'] and True
    
    for stock, ismet in buy_conditions.items():
        if all(ismet.values()):
            for df_name in tr_data.keys():
                if stock in df_name and '1분봉' in df_name:
                    price = tr_data[df_name]['현재가'][-1]
                    break
            orders['buy'].append((stock, price))
    for stock, ismet in sell_conditions.items():
        if all(ismet.values()):
            for df_name in tr_data.keys():
                if stock in df_name and '1분봉' in df_name:
                    price = tr_data[df_name]['현재가'][-1]
                    break            
            orders['sell'].append((stock, price))

    return orders

solds = {}
profits = {}

def auto_orders(self, orders):
    global orderstatus, solds, profits   
       
    for buys in orders[0]:
        for buying in buys:
            if orderstatus[buying[0]] == 'buying':
                buy(buying)
                orderstatus[buying[0]] = 'bought'
                profits[buying[0]] = {'bought':buying[1]}
    for sells in orders[1]:
        for selling in sells:
            if orderstatus[selling[0]] == 'selling':
                sell(selling)
                orderstatus[selling[0]] = 'sold'
                profits[selling[0]] = {'sold':selling[1]}
                    
     
for _ in range(30):   
    for stock in orderstatus.keys():
        if orderstatus[stock] == 'sold':
            solds[stock] = True
        else:
            solds[stock] = False
    if all(solds.values()):
        break                      
                    
    orders = self.find_buy_sell(breakdown(tr_data))
    if _ == 0:
        for buys in orders[0]:
            for buy in buys:
                orderstatus[buy[0]] = 'buying'
                
        for sells in orders[1]:
            for sell in sells:
                orderstatus[sell[0]] = 'selling'   
    self.auto_orders(orders) 

for stock, profit in profits.items():
    if profit['bought'] != 0 and profit['sold'] != 0:
        print(stock, ' :', (profit['sold']/profit['bought'] - 1) * 100, '%')
print(profits)
