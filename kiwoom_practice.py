from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
        # self.KOSPI_list = pd.DataFrame()
        
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

        self._event_handler()

        self._login()
        
        self.account_info()
        self.KOSPI_list = self.stock_ticker()
        self.remaining_data = False
        # self.db_sql('KOSPI')
   
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

        # self.KOSPI_list = pd.DataFrame(stock_list)
        # print(stock_list)
        # print(self.KOSPI_list)
        return stock_list
    
    def set_input_value(self, tr_name, tr_value):
        return self.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
    
    def comm_rq_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRQData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    # def db_sql(self, table):
    #     dbfile = sqlite3.connect(r'D:\myProjects\myKiwoom\KOSPI.db')
    #     cursor = dbfile.cursor()
    #     self.KOSPI_list.to_sql(table, cursor, if_exists='replace')

    def _login(self):
        self.dynamicCall('CommConnect')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def _event_handler(self):
        self.OnEventConnect.connect(self._comm_connect_event)
        self.OnReceiveTrData.connect(self._receive_tr_data)
    
    def _comm_connect_event(self, err_code):
        if err_code == 0:
            print('Successfully logged in')
        self.login_loop.exit()
        print('Login loop exited')
    
    def _receive_tr_data(self, scrno, rqname, trcode, recordname, prenext, datalen, errcode, message, splmmsg):
        if prenext == 2:
            self.remaining_data = True
        elif prenext == 0:
            self.remaining_data = False
        
        if rqname == 'opt10081_req':
            print('scrno, rqname, trcode, recordname, prenext, datalen, errcode, message, splmmsg: \n',\
                 scrno, rqname, trcode, recordname, prenext, datalen, errcode, message, splmmsg)
            self._opt10081(rqname, trcode, recordname)

        try:
            self.tr_event_loop.exit()

        except AttributeError:
            pass

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)

    def _opt10081(self, rqname, trcode, recordname):
        data_cnt = self._get_repeat_cont(trcode, recordname)

        for idx in range(data_cnt):
            date = self._get_comm_data(trcode, rqname, idx, '일자')
            open = self._get_comm_data(trcode, rqname, idx, '시가')
            high = self._get_comm_data(trcode, rqname, idx, '고가')
            low = self._get_comm_data(trcode, rqname, idx, '저가')
            close = self._get_comm_data(trcode, rqname, idx, '현재가')
            volume = self._get_comm_data(trcode, rqname, idx, '거래량')  
            print(date, open, high, low, close, volume)
    
    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()
 
app = QApplication(sys.argv)
kiwoom = Kiwoom()

kiwoom.set_input_value('종목코드', '039490')
kiwoom.set_input_value('기준일자', '20170224')
kiwoom.set_input_value('수정주가구분', 1)
kiwoom.comm_rq_data('opt10081_req', 'opt10081', 1, '0101')

# while kiwoom.remaining_data == True:
#     time.sleep(TR_REQ_TIME_INTERVAL)
#     kiwoom.set_input_value('종목코드', '039490')
#     kiwoom.set_input_value('기준일자', '20170224')
#     kiwoom.set_input_value('수정주가구분', 1)
#     kiwoom.comm_rq_data('opt10081_req', 'opt10081', 2, '0101')

# app.exec_()



