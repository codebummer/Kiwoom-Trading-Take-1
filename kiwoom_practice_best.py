from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys, os
from datetime import datetime

# import matplotlib.pyplot as plt
os.chdir(r'D:\myProjects\TradingDB')
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
        self.real_data = {'주식시세' : {}, '주식체결' : {}, '주문체결' : {}}
        self.fidlist = [
            10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 25, 26, 27, 28, 29, 30, 31, 32, 288,
            290, 302, 311, 567, 568, 691, 851, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909,
            910, 911, 912, 913, 914, 915, 919, 920, 921, 922, 923, 938, 939, 9001, 9201, 9203, 9205
        ]

        self.all_fids = {
            10:'현재가', 11:'전일대비', 12:'등락율', 13:'누적거래량', 14:'누적거래대금', 15:'거래량',
            16:'시가', 17:'고가', 18:'저가', 20:'체결시간', 23:'거래비용', 25:'전일대비기호', 26:'전일대비거래량대비',
            27:'매도호가', 28:'매수호가', 29:'거래대금증감', 30:'전일거래량대비', 31:'거래회전율', 32:'거래비용',
            288:'체결강도', 290:'장구분', 302:'종목명', 311:'시가총액(억)', 567:'상한가발생시간', 568:'하한가발생시간',
            691:'KO접근도', 851:'전일동시간거래량비율', 900:'주문수량', 901:'주문가격', 902:'미체결수량', 903:'체결누계금액',
            904:'원주문번호', 905:'주문구분', 906:'매매구분', 907:'매도수구분', 908:'주문/체결시간', 909:'체결번호',
            910:'체결가', 911:'체결량', 912:'주문업무분류', 913:'주문상태', 914:'단위체결가', 915:'단위체결량', 919:'거부사유',
            920:'화면번호', 921:'터미널번호', 922:'신용구분', 923:'대출일', 938:'당일매매수수료', 939:'당일매매세금',
            9001:'종목코드,업종코드', 9201:'계좌번호', 9203:'주문번호', 9205:'관리자사번'
        }

        self.fids_dict = {
            '주식시세' : {10:'현재가', 11:'전일대비', 12:'등락율', 27:'매도호가', 28:'매수호가',
                        13:'누적거래량', 14:'누적거래대금', 16:'시가', 17:'고가', 18:'저가', 25:'전일대비기호',
                        26:'전일거래량대비', 29:'거래대금증감', 30:'전일거래량대비' ,31:'거래회전율', 23:'거래비용',
                        311:'시가총액(억)', 567:'상한가발생시간', 568:'하한가발생시간'},
            '주식체결' : {20:'체결시간', 10:'현재가', 11:'전일대비', 12:'등락율', 27:'매도호가', 28:'매수호가',
                        15:'거래량', 13:'누적거래량', 14:'누적거래대금', 16:'시가', 17:'고가', 18:'저가', 25:'전일대비기호',
                        26:'전일거래량대비', 29:'거래대금증감', 30:'전일거래량대비', 31:'거래회전율', 32:'거래비용', 288:'체결강도',
                        311:'시가총액(억)', 290:'장구분', 691:'KO접근도', 567:'상한가발생시간', 568:'하한가발생시간', 851:'전일동시간거래량비율'},
            '주문체결' : {9201:'계좌번호', 9203:'주문번호', 9205:'관리자사번', 9001:'종목코드,업종코드', 912:'주문업무분류',
                        913:'주문상태', 302:'종목명', 900:'주문수량', 901:'주문가격', 902:'미체결수량', 903:'체결누계금액',
                        904:'원주문번호', 905:'주문구분', 906:'매매구분', 907:'매도수구분', 908:'주문/체결시간', 909:'체결번호', 
                        910:'체결가', 911:'체결량', 10:'현재가', 27:'매도호가', 28:'매수호가', 914:'단위체결가', 915:'단위체결량',
                        938:'당일매매수수료', 939:'당일매매세금', 919:'거부사유', 920:'화면번호', 921:'터미널번호', 922:'신용구분', 923:'대출일'}
        }

        # self.real_data = pd.DataFrame({
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
        self.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
    
    def set_real_data(self, scrno, codelist, fidlist, opttype):
        self.dynamicCall('SetRealReg(QString, QString, QString, QString)', scrno, codelist, fidlist, opttype)
        self.real_tr_event_loop = QEventLoop()
        self.real_tr_event_loop.exec_()
    
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
    
    def _receive_real_data(self, codelist, realtype, realdata):
        print('\nreceived real data - codelist, realtype, realdata: ', codelist, realtype, [realdata.split()])
        if realtype == '주식시세':
            self._realtype_stock_status(codelist)
        elif realtype == '주식체결':
            self._realtype_stock_made(codelist)
        elif realtype == '주문체결':
            self._realtype_order_made(codelist)


        try:
            self.real_tr_event_loop.exit()

        except AttributeError:
            pass

    def _realtype_stock_status(self, codelist):
        add = {}
        fidlist = self.fids_dict['주식시세']
        for code in codelist:
            for fidname in fidlist.values():
                add = {code : {fidname : []}}
        for code in codelist:
            for fid, fidname in fidlist.items():
                add[code][fidname].append(self._get_comm_real_data(code, fid))        
            self.real_data['주식시세'][code].append(add)
        print(add)

        if len(self.real_data['주식시세']) >= 100_000:
            for code in codelist:                
                df = pd.DataFrame(self.real_data['주식시세'][code])
                self._real_data_to_sql('주식시세', code, df, if_exists='append')
            self.real_data['주식시세'] = {}
        
    def _realtype_stock_made(self, codelist): 
        add = {}
        fidlist = self.fids_dict['주식체결']
        for code in codelist:
            for fidname in fidlist.values():
                add = {code : {fidname : []}}
        for code in codelist:
            for fid, fidname in fidlist.items():
                add[code][fidname].append(self._get_comm_real_data(code, fid))
            self.real_data['주식체결'][code].append(add)      
        print(add)

        if len(self.real_data['주식체결']) >= 100_000:
            for code in codelist:
                df = pd.DataFrame(self.real_data['주식체결'][code])
                self._real_data_to_sql('주식체결', code, df, if_exists='append')
            self.real_data['주식체결'] = {}
        
    def _realtype_order_made(self, codelist):
        add = {}
        fidlist = self.fids_dict['주문체결']
        for code in codelist:
            for fidname in fidlist.values():
                add = {code : {fidname : []}}
        for code in codelist:
            for fid, fidname in fidlist.items():
                add[code][fidname].append(self._get_comm_real_data(code, fid))
            self.real_data['주문체결'][code].append(add)      
        print(add)

        if len(self.real_data['주문체결']) >= 100_000:
            for code in codelist:
                df = pd.DataFrame(self.real_data['주문체결'][code])
                self._real_data_to_sql('주문체결', code, df, if_exists='append')
            self.real_data['주문체결'] = {}
         
    
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

    def static_data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')

    def _real_data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')

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
            
    def request_real_data(self, codelist, fidlist, opttype='1', scrno='0001'):
        self.set_real_data(scrno, codelist, fidlist, opttype)
    
 
app = QApplication(sys.argv)

kiwoom = Kiwoom()

kiwoom.request_daily_chart('900310', '20220101')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['Date'])
print(df)
kiwoom.static_data_to_sql('900310_Daily', '900310_Daily', df)
kiwoom.reset()
df = pd.DataFrame()

kiwoom.request_tick_chart('900310')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['Date'])
print(df)
kiwoom.static_data_to_sql('900310_Tick', '900310_Tick', df)
kiwoom.reset()


kiwoom.request_real_data(['900310', '005930', '005380'], kiwoom.fidlist)

# plt.plot(df.index[-100:], df.Close[-100:])
# plt.xticks(rotation=45)
# plt.show()
# app.exec_()



# # The following is part of a script to extract all fid list from above used variables
# a = [10, 11, 12, 27, 28, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 23, 311, 567, 568, 20, 10, 11, 12, 27, 28, 15, 13, 14, 16, 17, 18, 25, 26, 29, 30, 31, 32, 288, 311, 290, 691, 567, 568, 851, 9201, 9203, 9205, 9001, 912, 913, 302, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 10, 27, 28, 914, 915, 938, 939, 919, 920, 921, 922, 923]
# seen = set()
# unique = set()
# for x in a:
#     if x == seen:
#         seen.add(x)
#     else:
#         unique.add(x)
# seen
# unique = list(unique)
# unique.sort()
# unique

# fidlist = [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 23, 25, 26, 27, 28, 29, 30, 31, 32, 288, 290, 302, 311, 567, 568, 691, 851, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 919, 920, 921, 922, 923, 938, 939, 9001, 9201, 9203, 9205]
# len(fidlist)
