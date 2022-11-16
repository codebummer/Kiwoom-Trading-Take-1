from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd

import sys


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
        self.KOSPI_list = pd.DataFrame()
        
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
        self.event_handler()

        self.dynamicCall('CommConnect')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()
        
        self.account_info()
        self.stock_ticker()
        self.db_sql('KOSPI')
      
     
    def event_handler(self):
        self.OnEventConnect.connect(self.comm_connect_event)
    
    def comm_connect_event(self, err_code):
        if err_code == 0:
            print('Successfully logged in')
        self.login_loop.exit()
        print('Login loop exited')

    def account_info(self):
        account_num = self.dynamicCall('GetLoginInfo(QString)', ['ACCNO'])
        print(account_num.strip(';'))

    def stock_ticker(self):
        response = self.dynamicCall('GetCodeListByMarket(QString)', ['0'])
        tickers = response.split(';')
        stock_list = {}
        for ticker in tickers:
            stock = self.dynamicCall('GetMasterCodeName(QString)', [ticker])
            stock_list[ticker] = [stock]

        self.KOSPI_list = pd.DataFrame(stock_list)
        print(stock_list)
        print(self.KOSPI_list)
    
    def db_sql(self, table):
        dbfile = sqlite3.connect(r'D:\myProjects\myKiwoom\KOSPI.db')
        cursor = dbfile.cursor()
        self.KOSPI_list.to_sql(table, cursor, if_exists='replace')






app = QApplication(sys.argv)
kiwoom = Kiwoom()
app.exec_()



