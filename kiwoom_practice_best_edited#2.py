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
        
        self.fidlist = []
        self.real_tr_data ={}
        # self.real_tr_stocks = set() #list of dataframes that will be created to store real time data
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
        self.ohlcva = {'일자':[], '시가':[], '고가':[], '저가':[], '현재가':[], '거래량':[], '거래대금':[]}
        # self.real_data = {'주식시세' : {}, '주식체결' : {}, '주문체결' : {}}
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
        
    def _login(self):
        self.dynamicCall('CommConnect')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def _event_handlers(self):
        self.OnEventConnect.connect(self._comm_connect_event)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveRealData.connect(self._receive_real_data)
        # self.OnReceiveChejanData(self._receive_chejan_data)
    
    def _comm_connect_event(self, err_code):
        if err_code == 0:
            print('Successfully logged in')
           
        self.login_loop.exit()
        print('Login loop exited')
        
    # def _db_connect(self, filename):
    #     try:
    #         return sqlite3.connect(filename)            
    #     except ConnectionRefusedError:
    #         print('Connection to Database is Refuesed')            
    
    def static_data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')

    def _real_data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')
            
    # def _real_data_dictionary_to_sql(self, tablename, filename, data):
    #     with sqlite3.connect(filename) as file:
    #         cursor = file.cursor()              
    #         keys = ','.join(data.keys())
    #         qmarks = ','.join(list('?'*len(data.keys())))
    #         values = tuple(data.values())
    #         print('\n\nkeys: ', keys, '\n\nvalues: ', values)
    #         cursor.execute('INSERT INTO '+tablename+' ('+keys+') VALUES ('+qmarks+')', values)

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
        for code in codelist:
            self.dynamicCall('SetRealReg(QString, QString, QString, QString)', scrno, code, fidlist, opttype)
        self._event_loop_exec('real')
    
    def comm_rq_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRQData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self._event_loop_exec('tr')
        
    def comm_kw_rq_data(self, arrcode, prenext, codecnt, typeflag=0, rqname='OPTKWFID', scrno='0001'):
        self.dynamicCall('CommKwRqData(QString, int, int, int, QString, QString)', arrcode, prenext, codecnt, typeflag, rqname, scrno)
        self._event_loop_exec('big')
        
    def _event_loop_exec(self, loopname):
        exec(f'{loopname} = QEventLoop()\{loopname}.exec_()')
    
    def _event_loop_exit(self, loopname):
        exec(f'{loopname}.exit()')
    
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
        # elif rqname == 'OPTKWFID':
        #     self._optkwfid(trcode)

        try:
            self._event_loop_exit('tr')

        except AttributeError:
            pass
    
    def _receive_real_data(self, code, realtype, realdata):
        if realtype == '주식시세':
            self._realtype_stock_status(code)
        elif realtype == '주식체결':
            self._realtype_stock_made(code)
        elif realtype == '주문체결':
            self._realtype_order_made(code)

        # try:
        #     self._event_loop_exit('real')
        # except AttributeError:
        #     pass
        
    # def _receive_chejan_data(self, gubun, itemcnt, fidlist):
    #     if gubun == 0: #order placed and made 
    #         self._real_chejan_placed_made(itemcnt, fidlist)
    #     elif gubun == 1:
    #         self._domestic_balance_change()
        
    def _realtype_stock_status(self, code):
        add= {}
        fidlist = self.fids_dict['주식시세']
        # for fidname in fidlist.values():
        #     # add[code][fidname] = []
        #     add[fidname] = ''

        for fid, fidname in fidlist.items():
            add[fidname] = self._get_comm_real_data(code, fid)
        
        df_name, df = self._df_generator('주식시세', code, add)
        if len(df) > 1_000:
            self._real_data_to_sql('주식시세', f'{df_name}.db', df)
            self.real_tr_data[df_name] = pd.DataFrame()
 
    def _realtype_stock_made(self, code): 
        add= {}
        fidlist = self.fids_dict['주식체결']

        for fid, fidname in fidlist.items():
            add[fidname] = self._get_comm_real_data(code, fid)
        
        df_name, df = self._df_generator('주식체결', code, add)
        if len(df) > 1_000:
            self._real_data_to_sql('주식체결', f'{df_name}.db', df)
            self.real_tr_data[df_name] = pd.DataFrame()
 
    def _realtype_order_made(self, code):
        add= {}
        fidlist = self.fids_dict['주문체결']

        for fid, fidname in fidlist.items():
            add[fidname] = self._get_comm_real_data(code, fid)
        
        df_name, df = self._df_generator('주문체결', code, add)
        if len(df) > 1_000:
            self._real_data_to_sql('주문체결', f'{df_name}.db', df)
            self.real_tr_data[df_name] = pd.DataFrame()

    def _df_generator(self, realtype, stockcode, data):
        df_name = realtype+'_'+stockcode
        if df_name in self.real_tr_data.keys():
            self.real_tr_data[df_name] = self.real_tr_data[df_name].append(pd.DataFrame(data), ignore_index=True)
            return df_name, self.real_tr_data[df_name]
        else:
            self.real_tr_data[df_name] = pd.DataFrame(data)
            return df_name, self.real_tr_data[df_name]
    
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _real_chejan_placed_made(self, itemcnt, fidlist):        
        for idx in itemcnt:
            for fid in fidlist:
                print(self.dynamicCall('GetChejanData(int)', fid))
 
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

            self.ohlcva['일자'].append(date)
            self.ohlcva['시가'].append(int(open))
            self.ohlcva['고가'].append(int(high))
            self.ohlcva['저가'].append(int(low))
            self.ohlcva['현재가'].append(int(close))
            self.ohlcva['거래량'].append(int(volume))
            self.ohlcva['거래대금'].append(int(amount))

    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')   

        for idx in range(data_cnt):
            date = self._get_comm_data(trcode, rqname, idx, '체결시간')
            open = self._get_comm_data(trcode, rqname, idx, '시가')
            high = self._get_comm_data(trcode, rqname, idx, '고가')
            low = self._get_comm_data(trcode, rqname, idx, '저가')
            close = self._get_comm_data(trcode, rqname, idx, '현재가')
            volume = self._get_comm_data(trcode, rqname, idx, '거래량')

            self.ohlcva['일자'].append(date)
            self.ohlcva['시가'].append(int(open))
            self.ohlcva['고가'].append(int(high))
            self.ohlcva['저가'].append(int(low))
            self.ohlcva['현재가'].append(int(close))
            self.ohlcva['거래량'].append(int(volume))
            self.ohlcva['거래대금'].append(None)
    
    # def _optkwfid(self, trcode):
 
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
            
    def request_real_data(self, codelist, fidlist, opttype='1', scrno='0001'):
        self.set_real_data(scrno, codelist, fidlist, opttype)
    
 
app = QApplication(sys.argv)

kiwoom = Kiwoom()

kiwoom.request_daily_chart('900310', '20220101')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['일자'])
print(df)
kiwoom.static_data_to_sql('900310_Daily', '900310_Daily.db', df)
kiwoom.reset()
df = pd.DataFrame()

kiwoom.request_tick_chart('900310')
df = pd.DataFrame(kiwoom.ohlcva, index=kiwoom.ohlcva['일자'])
print(df)
kiwoom.static_data_to_sql('900310_Tick', '900310_Tick.db', df)
kiwoom.reset()

kiwoom.request_real_data(['900310', '005930', '005380'], kiwoom.fidlist)
