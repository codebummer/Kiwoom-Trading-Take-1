from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys
from datetime import datetime
import matplotlib.pyplot as plt

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
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
        self.status_column = ['Current', 'FromYesterday', 'Change%', 'Ask', 'Bid', 'VolumeAccummulated', 
                            'AmountAccumulated', 'Open', 'High', 'Low', 'PlusMinusFromYesterday',
                            'VolumeFromYesterday', 'AmountChange', 'AmountChangeRatio', 'TransactionTurnOut',
                            'TransactionCost', 'MarketCap', 'HighTime', 'LowTime']
        self.stock_status = []
        self.tr_made = []
        # self.stock_status = pd.DataFrame({
        #     'Current' : [],
        #     'FromYesterday' : [],
        #     'Change%' : [],
        #     'Ask' : [], #sell
        #     'Bid' : [], #buy
        #     'VolumeAccummulated' : [],
        #     'AmountAccumulated' : [],
        #     'Open' : [],
        #     'High' : [],
        #     'Low' : [],
        #     'PlusMinusFromYesterday' : [],
        #     'VolumeFromYesterday' : [],
        #     'AmountChange' : [],
        #     'AmountChangeRatio' : [],
        #     'TransactionTurnOut' : [],
        #     'TransactionCost' : [],
        #     'MarketCap' : [], #thousand million
        #     'HighTime' : [],
        #     'LowTime' : []
        # })


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
        return stock_list
    
    def set_input_value(self, tr_name, tr_value):
        return self.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
    
    def comm_rq_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRQData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    def _login(self):
        self.dynamicCall('CommConnect')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def _event_handlers(self):
        self.OnEventConnect.connect(self._comm_connect_event)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveRealData.connect(self._receive_real_data)
    
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
        elif rqname == 'OPT10079':
            print('scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4: \n',\
                 scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4)
            self._opt10079(rqname, trcode)

        try:
            self.tr_event_loop.exit()

        except AttributeError:
            pass
    
    def _receive_real_data(self, code, realtype, realdata):
        if realtype == '주식시세':
            self._realtype_stock_status(code)
        # if realtype == '주식체결':
        #     self._realtype_tr_made(code)

    def _realtype_stock_status(self, code):
        fid = [10, 11, 12, 27, 28, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 32, 311, 567, 568]
        add = []
        for id in fid:
            add.append(self._get_comm_real_data(code, id))        
        self.stock_status.append([add])
        print(add)

        if len(self.stock_status) == 5_000:
            status = pd.DataFrame(self.stock_status, columns=self.status_column)
            self._data_to_sql('Stock_Status', status)
            self.stock_status = []
        
    # def _realtype_tr_made(self, code):
    #     fid = [20, 10, 11, 12, 27, 28, 15, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 32, 228, 311, 290, 691, 567, 568, 851]
    #     add = []
    #     for id in fid:
    #         add.append(self._get_comm_real_data(code, id))
    #     self.tr_made.append([add])
    #     print(add)
    
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)

    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')

        for idx in range(data_cnt):
            date = self._get_comm_data(trcode, rqname, idx, '일자')
            open = self._get_comm_data(trcode, rqname, idx, '시가')
            high = self._get_comm_data(trcode, rqname, idx, '고가')
            low = self._get_comm_data(trcode, rqname, idx, '저가')
            close = self._get_comm_data(trcode, rqname, idx, '현재가')
            volume = self._get_comm_data(trcode, rqname, idx, '거래량')
            amount = self._get_comm_data(trcode, rqname, idx, '거래대금')

            self.ohlcva['Date'].append(date)
            self.ohlcva['Open'].append(int(open))
            self.ohlcva['High'].append(int(high))
            self.ohlcva['Low'].append(int(low))
            self.ohlcva['Close'].append(int(close))
            self.ohlcva['Volume'].append(int(volume))
            self.ohlcva['Amount'].append(int(amount))

    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')   

        for idx in range(data_cnt):
            date = self._get_comm_data(trcode, rqname, idx, '체결시간')
            open = self._get_comm_data(trcode, rqname, idx, '시가')
            high = self._get_comm_data(trcode, rqname, idx, '고가')
            low = self._get_comm_data(trcode, rqname, idx, '저가')
            close = self._get_comm_data(trcode, rqname, idx, '현재가')
            volume = self._get_comm_data(trcode, rqname, idx, '거래량')

            self.ohlcva['Date'].append(date)
            self.ohlcva['Open'].append(int(open))
            self.ohlcva['High'].append(int(high))
            self.ohlcva['Low'].append(int(low))
            self.ohlcva['Close'].append(int(close))
            self.ohlcva['Volume'].append(int(volume))
            self.ohlcva['Amount'].append(None)
           

    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()

    def request_daily_chart(self, stockcode, date, pricetype=1):
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('기준일자', date)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10081', 'opt10081', 0, '0001')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('기준일자', date)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10081', 'opt10081', 2, '0001')
    
    def request_tick_chart(self, stockcode, ticktime=1, pricetype=1):
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('틱범위', ticktime)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10079', 'opt10079', 0, '0001')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('틱범위', ticktime)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10079', 'opt10079', 2, '0001')
    
    def _data_to_sql(self, tablename, df):
        path = r'D:\myProjects\myKiwoom\900310.db'
        with sqlite3.connect(path) as file:
            df.to_sql(tablename, file, if_exists='append')


def save_in_sq(tablename, df):
    # ticktime = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')    
    # path = f'D:/myProjects/myKiwoom/algotrading_data_{ticktime}.db'
    path = r'D:\myProjects\myKiwoom\900310.db'
    with sqlite3.connect(path) as file: 
        df.to_sql(tablename, file, if_exists='replace')
 
app = QApplication(sys.argv)

kiwoom = Kiwoom()

kiwoom.request_daily_chart('900310', '20170224')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['Date'])
print(df)
save_in_sq('900310_Daily', df)
kiwoom.reset()
df = pd.DataFrame()

kiwoom.request_tick_chart('900310')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['Date'])
print(df)
save_in_sq('900310_Tick', df)
kiwoom.reset()

# plt.plot(df.index[-100:], df.Close[-100:])
# plt.xticks(rotation=45)
# plt.show()
# app.exec_()



