import sqlite3
from PyQt5.QtCore import *
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
import pandas as pd
import pandas_datareader.data as web
import datetime
import matplotlib
import sys
import functools

# Take daily stock price records from online and arhive them in a database

class databasization():

    def set_full_path(self, filename):
        path = 'D:/myProjects/myKiwoom/'
        self.full_path = path + filename

    def dateset(self, date_input):
        return datetime.datetime(date_input[0], date_input[1], date_input[2])

    # First step to use a database. Instantiate a sqlite3.connect object.
    def create_connection_to_db(self):
        with sqlite3.connect(self.full_path) as connection:
            print(f'Successfully connected to {self.full_path}')
        return connection

    # Download daily stock prices from Yahoo and put them in a dataframe
    def data_reader(self, ticker, start, end):
        # pandas_datareader.data.DataReader() downloads data in a dataframe format
        df = web.DataReader(ticker, 'yahoo', start, end) 
        print('Daily Prices Successfully Downloaded')
        return df

    # Put the price data in a dataframe format into a sqlite3 database, using to_sql()
    def df_to_db_archiver(self, df, table, connection):
        df.to_sql(table, connection)
        print(f'Price Data Archived in {self.full_path}')


# Decorator to instantiate database creations
def create_stock_db_instantiation(func):
    @functools.wraps(func)
    def wrapper(stock_info: dict):
        inst = func(stock_info)
        inst.set_full_path(stock_info['file'])
        start = inst.dateset(stock_info['start'])
        end = inst.dateset(stock_info['end'])
        inst_db = inst.create_connection_to_db()
        inst_df = inst.data_reader(stock_info['ticker'], start, end)
        inst.df_to_db_archiver(inst_df, stock_info['table'], inst_db)
    return wrapper

# Database creator
@create_stock_db_instantiation
def make_stock_db(stock_info: dict):
    return databasization()

stocks_of_interest = [
    {
        'file' : 'Samsung.db',
        'ticker' : '005930.KS',
        'table' : 'Samsung Daily Prices',
        'start': [2010, 1, 1],
        'end': [2022, 3, 18]
    },
    {
        'file' : 'Hite_Jino_Holdings.db',
        'ticker' : '000140.KS',
        'table' : 'Hite Jino Holdings Daily Prices',
        'start' : [2010, 1, 1],
        'end' : [2022, 3, 18]
    },
    {
        'file' : 'POSCO.db',
        'ticker' : '005490.KS',
        'table' : 'POSCO Daily Prices',
        'start': [2010, 1, 1],
        'end': [2022, 3, 18]
    },
    {
        'file' : 'LG_Electronics.db',
        'ticker' : '066570.KS',
        'table' : 'LG Electronics Daily Prices',
        'start': [2010, 1, 1],
        'end': [2022, 3, 18]
    }    
]

'''
Feed elements of a multi-demensional list one at each
This is the same as unpacking operator (*)

functools.reduce(make_stock_db, *stock_of_interest)
The above one line statement is the same as the below four line statements 

def stock_list_generator(lists):
    for one_stock_info in lists:
        yield one_stock_info
functools.reduce(make_stock_db, stock_list_generator(stocks_of_interest)) # functools.reduce() flattens or reduces higer dimension lists



stocks_of_interest = [
    ['Samsung.db', '005930.KS', 'Samsung Daily Prices', {'start': [2010, 1, 1], 'end': [2022, 3, 18]}],
    ['Hite_Jino_Holdings.db', '000140.KS', 'Hite Jino Holdings Daily Prices', {'start': [2010, 1, 1], 'end': [2022, 3, 18]}],
    ['POSCO.db', '005490.KS', 'POSCO Daily Prices', {'start': [2010, 1, 1], 'end': [2022, 3, 18]}],
    ['LG_Electronics.db', '066570.KS', 'LG Electronics Daily Prices', {'start': [2010, 1, 1], 'end': [2022, 3, 18]}]    
]
'''



class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self._instantiate_kiwoom()
        self.comm_connect()
    
    def _instantiate_kiwoom(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def comm_connect(self):
        self.dynamicCall('CommConnect()')
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def set_signal_slots(self):
        self.OnEventConnect(self.connect_signal_slot)
        
    
    def set_input_values(self, tr_input_name, tr_input_value):
        self.SetInputValue(tr_input_name, tr_input_value)

    def connect_signal_slot(self, errcode):
        # print(self.connect_signal_slot)
        if errcode == 0:
            print('Successfully Connected')
        else:
            print('Connection Failed')
        
        self.login_event_loop.exit()
 
if __name__ == '__main__':    
    
    for stock_details in stocks_of_interest:
        make_stock_db(stock_details)

    # app = QApplication(sys.argv)
    # kiwoom = Kiwoom()
    # app.exec_()
