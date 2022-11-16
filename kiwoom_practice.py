from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys
from datetime import datetime

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
        # self.KOSPI_list = pd.DataFrame()

        self.reset()
        self.OCX_available()      
        self._event_handlers()
        self._login()
        
        self.account_info()
        self.KOSPI_list = self.stock_ticker()        


    def OCX_available(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def reset(self):
        self.remaining_data = False
        self.ohlcva = {'Date':[], 'Open':[], 'High':[], 'Low':[], 'Close':[], 'Volume':[], 'Amount':[]}
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

    def _event_handlers(self):
        self.OnEventConnect.connect(self._comm_connect_event)
        self.OnReceiveTrData.connect(self._receive_tr_data)
    
    def _comm_connect_event(self, err_code):
        if err_code == 0:
            print('Successfully logged in')
        self.login_loop.exit()
        print('Login loop exited')
    
    def _receive_tr_data(self, scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4):
        if prenext == 2:
            self.remaining_data = True
        elif prenext == 0:
            self.remaining_data = False
        
        if rqname == 'OPT10081':
            print('scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4: \n',\
                 scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4)
            self._opt10081(rqname, trcode)

        try:
            self.tr_event_loop.exit()

        except AttributeError:
            pass

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)

    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')

        for idx in range(data_cnt):
            self.ohlcva['Date'].append(self._get_comm_data(trcode, rqname, idx, '일자'))
            self.ohlcva['Open'].append(int(self._get_comm_data(trcode, rqname, idx, '시가')))
            self.ohlcva['High'].append(int(self._get_comm_data(trcode, rqname, idx, '고가')))
            self.ohlcva['Low'].append(int(self._get_comm_data(trcode, rqname, idx, '저가')))
            self.ohlcva['Close'].append(int(self._get_comm_data(trcode, rqname, idx, '현재가')))
            self.ohlcva['Volume'].append(int(self._get_comm_data(trcode, rqname, idx, '거래량')))
            self.ohlcva['Amount'].append(int(self._get_comm_data(trcode, rqname, idx, '거래대금')))   
               

    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()

    def order_daily_chart(self, code, date, recordtype=1):
        self.set_input_value('종목코드', code)
        self.set_input_value('기준일자', date)
        self.set_input_value('수정주가구분', recordtype)
        self.comm_rq_data('OPT10081', 'opt10081', 1, '0101')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', code)
            self.set_input_value('기준일자', date)
            self.set_input_value('수정주가구분', recordtype)
            self.comm_rq_data('OPT10081', 'opt10081', 2, '0101')

def save_in_sq(tablename, df):
    path = r'D:\myProjects\myKiwoom\algotrading_data.db'
    with sqlite3.connect(path) as file: 
        df.to_sql(tablename, file, if_exists='replace')
 
app = QApplication(sys.argv)

kiwoom = Kiwoom()
kiwoom.order_daily_chart('039490', '20170224')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['Date'])
print(df)
save_in_sq('039490', df)

# app.exec_()



