from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *

import sys


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
        self.event_handler()

        self.dynamicCall('CommConnect')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()
        
        self.account_info()
        self.stock_ticker()
     
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
        stock_list = []
        for ticker in tickers:
            stock = self.dynamicCall('GetMasterCodeName(QString)', [ticker])
            stock_list.append(stock + ' : ' + ticker)
        
        print(stock_list)


app = QApplication(sys.argv)
kiwoom = Kiwoom()
app.exec_()



