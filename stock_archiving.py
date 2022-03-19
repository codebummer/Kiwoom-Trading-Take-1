import sqlite3
from PyQt5.QtCore import *
from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
import pandas as pd
import pandas_datareader.data as web
import datetime
import matplotlib
import sys

class databasization():
    # def __init__(self):  
    #     self._path = 'D:/myProjects/myKiwoom/'

    def set_full_path(self, filename):
        path = 'D:/myProjects/myKiwoom/'
        self.full_path = path + filename

    def dateset(self, yy, mm, dd):
        return datetime.datetime(yy, mm, dd)
   
    def create_connection(self):
        with sqlite3.connect(self.full_path) as connection:
            print(f'Successfully connected to {self.full_path}')
        return connection

    def data_reader(self, ticker, start, end):
        df = web.DataReader(ticker, 'yahoo', start, end)
        print('Daily Prices Successfully Downloaded')
        return df

    def df_to_db_archiver(self, df, table, connection):
        df.to_sql(table, connection)
        print(f'Price Data Archived in {self.full_path}')

    # connection = create_connection(path)
    # cursor = connection.cursor()

    # posco_df = data_reader('005490.KS', start, end)
    # df_to_db_archiver(posco_df, 'POSCO Daily Prices', connection)


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
        self.comm_connect()
    
    def comm_connect(self):
        self.dynamicCall('CommConnect()')
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

if __name__ == '__main__':    
    # db_file = 'POSCO.db'
    # start = datetime.datetime(2010, 1, 1)
    # end = datetime.datetime(2022, 3, 19)

    # posco = databasization()
    # posco_db = posco.create_connection(db_file)
    # posco_df = posco.data_reader('005490.KS', start, end)
    # posco.df_to_db_archiver(posco_df, 'POSCO Daily Prices', posco_db)

    # hiteholdings = databasization()
    # hiteholdings.set_full_path('HiteJino_Holdings.db')
    # start = hiteholdings.dateset(2010, 1, 1)
    # end = hiteholdings.dateset(2022, 3, 19)
    # hiteholdings_db = hiteholdings.create_connection()
    # hiteholdings_df = hiteholdings.data_reader('000140.KS', start, end)
    # hiteholdings.df_to_db_archiver(hiteholdings_df, 'Hite Jino Holdings Daily Prices', hiteholdings_db)

    samsung = databasization()
    samsung.set_full_path('Samsung.db')
    start = samsung.dateset(2010, 1, 1)
    end = samsung.dateset(2022, 3, 19)
    samsung_db = samsung.create_connection()
    samsung_df = samsung.data_reader('005930.KS', start, end)
    samsung.df_to_db_archiver(samsung_df, 'Samsung Daily Prices', samsung_db)

    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    app.exec_()


