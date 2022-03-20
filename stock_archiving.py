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
        path = 'C:/myProjects/My-pyKiwwom1/'
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
    def wrapper(*args, **kwargs):
        inst = func(*args, **kwargs)
        inst.set_full_path(args[0])
        start = inst.dateset(kwargs['start'])
        end = inst.dateset(kwargs['end'])
        inst_db = inst.create_connection_to_db()
        inst_df = inst.data_reader(args[1], start, end)
        inst.df_to_db_archiver(inst_df, args[2], inst_db)
    return wrapper

# Database creator
@create_stock_db_instantiation
def make_stock_db(db_file_name, stock_ticker, db_table_name, start_date: dict, end_dates: dict):
    return databasization()


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

    make_stock_db('LG.db', '003550.KS', 'LG Daily Price', start = [2010, 1, 1], end = [2022, 3, 18])
       

    # app = QApplication(sys.argv)
    # kiwoom = Kiwoom()
    # app.exec_()
