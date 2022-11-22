from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys, os
from datetime import datetime
# import matplotlib.pyplot as plt

#change the current working directory
# path = r'D:\myprojects\TradingDB' + '\\' + datetime.today().strftime('%Y-%m-%d')
path = r'D:\myprojects\TradingDB'
if not os.path.exists(path):
     os.mkdir(path)
os.chdir(path) 

TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        
        self.fidlist = []
        self.tr_data = {}
        self.stockcode_non_realtime = 0
        self.requesting_time_unit = ''
        self.starting_time, self.lapse, self.SAVING_INTERVAL = time.time(), 0, 60*10
        self.reset()
        self.OCX_available()      
        self._event_handlers()
        self._login()
        
        self.account_info()
        self.all_stocks = self.stock_ticker()        

    def OCX_available(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def reset(self):
        self.remaining_data = False
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
                        938:'당일매매수수료', 939:'당일매매세금', 919:'거부사유', 920:'화면번호', 921:'터미널번호', 922:'신용구분', 923:'대출일'},
            '잔고수신' : {9201:'계좌번호', 9203:'주문번호', 9001:'종목코드', 913:'주문상태', 302:'종목명', 900:'주문수량', 901:'주문가격', 
                        902:'미체결수량', 903:'체결누계금액', 904:'원주문번호', 905:'주문구분', 906:'매매구분', 907:'매도수구분', 
                        908:'주문/체결시간', 9009:'체결번호', 910:'체결가', 911:'체결량', 10:'현재가', 27:'(최우선)매도호가', 
                        28:'(최우선)매수호가', 914:'단위체결가', 915:'단위체결량', 919:'거부사유', 920:'화면번호', 917:'신용구분', 
                        916:'대출일', 930:'보유수량', 931:'매입단가', 932:'총매입가', 933:'주문가능수량', 945:'당일순매수수량', 
                        946:'매도/매수구분', 950:'당일총매도손일', 951:'예수금', 307:'기준가', 8019:'손익율', 957:'신용금액', 958:'신용이자',
                        918:'만기일', 990:'당일실현손익(유가)', 991:'당일실현손익률(유가)', 993:'당일실현손익률(신용)', 397:'파생상품거래단위',
                        305:'상한가', 306:'하한가'}
        }
        self.orders_dict = {
            '호가구분' : {'00':'지정가', '03':'시장가', '05':'조건부지정가', '06':'최유리지정가', '07':'최우선지정가', '10':'지정가IOC', '13':'시장가IOC', 
                        '16':'최유리IOC', '20':'지정가FOK', '23':'시장가FOK', '26':'최유리FOK', '61':'장전시간외종가', '62':'시간외단일가매매', '81':'장후시간외종가'},
            '주문리턴' : {0:'주문성공', -308:'1초5회이상주문에러'}
        }
        
    def _login(self):
        self.dynamicCall('CommConnect')
        self._event_loop_exec('login_loop')

    def _event_handlers(self):
        self.OnEventConnect.connect(self._comm_connect_event)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveRealData.connect(self._receive_real_data)
        self.OnReceiveMsg.connect(self._receive_msg)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)
    
    def _comm_connect_event(self, err_code):
        if err_code == 0:
            print('Successfully logged in')
           
        self._event_loop_exit('login_loop')
        print('Login loop exited')
        
    def data_from_sql(self, tablename, filename):
        with sqlite3.connect(filename) as file:
            return pd.read_sql(f'SELECT * FROM [{tablename}]', file)    
    
    def _data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')
            
    def account_info(self):
        account_num = self.dynamicCall('GetLoginInfo(QString)', ['ACCNO'])
        print(account_num.strip(';'))

    def stock_ticker(self):
        response = self.dynamicCall('GetCodeListByMarket(QString)', ['']) # '' means all markets. '0' means KOSPI. '10' means KOSDAQ.
        tickers = response.split(';')
        stock_list = {}
        for ticker in tickers:
            stock = self.dynamicCall('GetMasterCodeName(QString)', [ticker])
            stock_list[ticker] = [stock]
            stock_list[stock] = ticker
        return stock_list
    
    def set_input_value(self, tr_name, tr_value):
        self.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
    
    def set_real_data(self, scrno, codelist, fidlist, opttype):
        for idx, code in enumerate(codelist):
            print(f'\n\nrequesting data of {code}')
            self.dynamicCall('SetRealReg(QString, QString, QString, QString)', f'00{idx+100}', code, fidlist, opttype)
                
        self._event_loop_exec('real')
        
    def set_order(self, rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno):
        self.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno)
    
    def comm_rq_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRQData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self._event_loop_exec('tr')
        
    def comm_kw_rq_data(self, arrcode, prenext, codecnt, typeflag=0, rqname='OPTKWFID', scrno='0005'):
        self.dynamicCall('CommKwRqData(QString, int, int, int, QString, QString)', arrcode, prenext, codecnt, typeflag, rqname, scrno)
        self._event_loop_exec('big')
        
    def _event_loop_exec(self, loopname):
        exec(f'self.{loopname} = QEventLoop()')
        exec(f'self.{loopname}.exec_()')
    
    def _event_loop_exit(self, loopname):
        exec(f'self.{loopname}.exit()')
    
    def _receive_tr_data(self, scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4):
        if prenext == 2:
            self.remaining_data = True
        elif prenext == 0:
            self.remaining_data = False
            
        print('scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4: ->in _receive_tr_data\n',\
                scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4)        

        if rqname == 'OPT10081':
            self._opt10081(rqname, trcode)
        elif rqname == 'OPT10079':
            self._opt10079(rqname, trcode)
        elif rqname == 'OPT10080':
            self._opt10080(rqname, trcode)
        elif rqname == 'OPTKWFID':
            self._optkwfid(trcode)

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
    
    def _receive_msg(self, scrno, rqname, trcode, msg):
        print('\n\nscrno, rqname, trcode, msg in receive_msg: ->in _receive_tr_data\n', scrno, rqname, trcode, msg)
        
 
        # try:
        #     self._event_loop_exit('real')
        # except AttributeError:
        #     pass
        
    def _receive_chejan_data(self, gubun, itemcnt, fidlist):
        if gubun == 0: #order placed and made 
            self._real_chejan_placed_made(itemcnt, fidlist)
        elif gubun == 1:
            self._domestic_balance_change(itemcnt, fidlist)
        if fidlist in self.orders_dict['호가구분'].keys():
            add = {}
            for fid in fidlist:
                add[self.orders_dict['호가구분'][fid]] = self._get_chejan_data(fid)
            print('\n\nhogagubun in receive chejan data: ', add)
        
    def _realtype_stock_status(self, code):
        add= {}
        fidlist = self.fids_dict['주식시세']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주식시세', code, add)
        self.lapse = time.time()
        if len(df) > 10 or self.lapse - self.starting_time > self.SAVING_INTERVAL:
            self.starting_time = time.time()
            self._data_to_sql('주식시세', df_name+'.db', df)            
            self.tr_data[df_name] = pd.DataFrame()
 
    def _realtype_stock_made(self, code): 
        add= {}
        fidlist = self.fids_dict['주식체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주식체결', code, add)
        self.lapse = time.time()
        if len(df) > 10 or self.lapse - self.starting_time > self.SAVING_INTERVAL:
            self.starting_time = time.time()
            self._data_to_sql('주식체결', df_name+'.db', df)
            self.tr_data[df_name] = pd.DataFrame()
 
    def _realtype_order_made(self, code):
        add= {}
        fidlist = self.fids_dict['주문체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]

        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주문체결', code, add)        
        self.lapse = time.time()
        if len(df) > 10 or self.lapse - self.starting_time > self.SAVING_INTERVAL:
            self.starting_time = time.time()
            self._data_to_sql('주문체결', df_name+'.db', df)
            self.tr_data[df_name] = pd.DataFrame()

    def _df_generator(self, realtype, stockcode, data):
        print('\n\nrealtype, stockcode, stock, data in df_generator: \n', realtype, stockcode, self.all_stocks[stockcode][0], data)
        df_name = self.all_stocks[stockcode][0]+'_'+realtype+self.requesting_time_unit+'_'+datetime.today().strftime('%Y_%m_%d')
        if df_name in self.tr_data.keys():
            self.tr_data[df_name] = self.tr_data[df_name].append(pd.DataFrame(data), ignore_index=True)
            return df_name, self.tr_data[df_name]
        else:
            self.tr_data[df_name] = pd.DataFrame(data)
            return df_name, self.tr_data[df_name]
    
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _real_chejan_placed_made(self, itemcnt, fidlist):        
        for idx in itemcnt:
            for fid in fidlist:
                print(self.dynamicCall('GetChejanData(int)', fid))
    
    def _get_chejan_data(self, fid):
        return self.dynamicCall('GetChejanData(int)', fid)

    def _opt10080(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식분봉차트')

        add = {}
        for idx in range(data_cnt):
            add['현재가'] = [self._get_comm_data(trcode, rqname, idx, '현재가')]
            add['거래량'] = [self._get_comm_data(trcode, rqname, idx, '거래량')]
            add['체결시간'] = [self._get_comm_data(trcode, rqname, idx, '체결시간')]
            add['시가'] = [self._get_comm_data(trcode, rqname, idx, '시가')]
            add['고가'] = [self._get_comm_data(trcode, rqname, idx, '고가')]
            add['저가'] = [self._get_comm_data(trcode, rqname, idx, '저가')]
            add['수정주가구분'] = [self._get_comm_data(trcode, rqname, idx, '수정주가구분')]
            add['수정비율'] = [self._get_comm_data(trcode, rqname, idx, '수정비율')]
            add['대업종구분'] = [self._get_comm_data(trcode, rqname, idx, '대업종구분')]
            add['소업종구분'] = [self._get_comm_data(trcode, rqname, idx, '소업종구분')]
            add['종목정보'] = [self._get_comm_data(trcode, rqname, idx, '종목정보')]
            add['수정주가이벤트'] = [self._get_comm_data(trcode, rqname, idx, '수정주가이벤트')]
            add['전일종가'] = [self._get_comm_data(trcode, rqname, idx, '전일종가')]
        
        
        df_name, df = self._df_generator('주식분봉차트', self.stockcode_non_realtime, add)
        self._data_to_sql('주식분봉차트', df_name+'.db', df)   
        print('\n\n_opt10080 request received:\n', self.tr_data[df_name])          
        self.tr_data[df_name] = pd.DataFrame()
 
    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')

        add = {}
        for idx in range(data_cnt):
            add['일자'] = [self._get_comm_data(trcode, rqname, idx, '일자')]
            add['시가'] = [self._get_comm_data(trcode, rqname, idx, '시가')]
            add['고가'] = [self._get_comm_data(trcode, rqname, idx, '고가')]
            add['저가'] = [self._get_comm_data(trcode, rqname, idx, '저가')]
            add['현재가'] = [self._get_comm_data(trcode, rqname, idx, '현재가')]
            add['거래량'] = [self._get_comm_data(trcode, rqname, idx, '거래량')]
            add['거래대금'] = [self._get_comm_data(trcode, rqname, idx, '거래대금')]

        for idx, key in enumerate(add.keys()):
            if idx == 0:
                continue                       
            add[key] = int(add[key][0])                       
   
        df_name, df = self._df_generator('주식분봉차트', self.stockcode_non_realtime, add)
        self._data_to_sql('주식분봉차트', df_name+'.db', df)     
        print('\n\n_opt10081 request received:\n', self.tr_data[df_name])                
        self.tr_data[df_name] = pd.DataFrame()

    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')
           
        add = {}
        for idx in range(data_cnt):
            add['체결시간'] = [self._get_comm_data(trcode, rqname, idx, '체결시간')]
            add['시가'] = [self._get_comm_data(trcode, rqname, idx, '시가')]
            add['시가'] = [self._get_comm_data(trcode, rqname, idx, '시가')]
            add['고가'] = [self._get_comm_data(trcode, rqname, idx, '고가')]
            add['저가'] = [self._get_comm_data(trcode, rqname, idx, '저가')]
            add['현재가'] = [self._get_comm_data(trcode, rqname, idx, '현재가')]
            add['거래량'] = [self._get_comm_data(trcode, rqname, idx, '거래량')]
            
        for idx, key in enumerate(add.keys()):
            if idx == 0:
                continue                       
            add[key] = int(add[key][0])                       
    
        df_name, df = self._df_generator('주식틱차트', self.stockcode_non_realtime, add)
        self._data_to_sql('주식틱차트', df_name+'.db', df)       
        print('\n\n_opt10079 request received:\n', self.tr_data[df_name])                                 
        self.tr_data[df_name] = pd.DataFrame()
    
    def _optkwfid(self, trcode):
        data_cnt = self._get_repeat_cont(trcode, '관심종목')
        
        add= {}
        for idx in range(data_cnt):
            add['종목코드'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '종목코드')] #0
            add['종목명'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '종목명')] #1
            add['현재가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '현재가')]
            add['기준가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '기준가')]
            add['전일대비'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '전일대비')]
            add['전일대비기호'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '전일대비기호')]
            add['등락율'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '등락율')] #6
            add['거래량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '거래량')]
            add['거래대금'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '거래대금')]
            add['체결량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '체결량')]
            add['체결강도'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '체결강도')] #10
            add['전일거래량대비'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '전일거래량대비')] #11
            add['매도호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도호가')]
            add['매수호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수호가')]
            add['매도1차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도1차호가')]
            add['매도2차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도2차호가')]
            add['매도3차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도3차호가')]
            add['매도4차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도4차호가')]
            add['매도5차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매도5차호가')]
            add['매수1차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수1차호가')]
            add['매수2차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수2차호가')]
            add['매수3차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수3차호가')]
            add['매수4차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수4차호가')]
            add['매수5차호가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '매수5차호가')]
            add['상한가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '상한가')]
            add['하한가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '하한가')]
            add['시가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '시가')]
            add['고가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '고가')]
            add['저가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '저가')]
            add['종가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '종가')]
            add['체결시간'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '체결시간')]
            add['예상체결가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '예상체결가')]
            add['예상체결량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '예상체결량')]
            add['자본금'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '자본금')]
            add['액면가'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '액면가')]
            add['시가총액'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '시가총액')]
            add['주식수'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '주식수')]
            add['호가시간'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '호가시간')]
            add['일자'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '일자')]
            add['우선매도잔량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '우선매도잔량')]
            add['우선매수잔량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '우선매수잔량')]
            add['우선매도건수'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '우선매도건수')]
            add['우선매수건수'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '우선매수건수')]
            add['총매도잔량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '총매도잔량')]
            add['총매수잔량'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '총매수잔량')]
            add['총매도건수'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '총매도건수')]
            add['총매수건수'] = [self._get_comm_data(trcode, 'OPTKWFID', idx, '총매수건수')]
        
        for idx, key in enumerate(add.keys()):
            if idx in [0, 1]:
                continue
            if idx in [6, 10, 11]:
                add[key] = float(add[key][0])
            add[key] = int(add[key][0])

        print('\n\n_optkwfid request received: \n', add)
  
        # df_name, df = self._df_generator('관심종목', self.stockcode_non_realtime, add)
        # self._data_to_sql('관심종목', df_name+'.db', df)
        # print('\n\n_optkwfid request received:\n', self.tr_data[df_name])                    
        # self.tr_data[df_name] = pd.DataFrame()
 
    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()

    def request_daily_chart(self, stock, date, pricetype=1):
        stockcode = self.all_stocks[stock]
        self.stockcode_non_realtime = stockcode        
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('기준일자', date)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10081', 'opt10081', 0, '0001')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('기준일자', date)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10081', 'opt10081', 2, '0002')

    def request_minute_chart(self, stock, mintime=30, pricetype=1):
        '''
        stock: name of a stock
        ticktime: one of 1, 3, 5, 10, 15, 30, 45, 60 
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        stockcode = self.all_stocks[stock]
        self.stockcode_non_realtime = stockcode      
        self.requesting_time_unit = str(mintime)+'분'
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('틱범위', mintime)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10080', 'opt10080', 0, '0003')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('틱범위', mintime)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10080', 'opt10080', 2, '0004')
    
    def request_tick_chart(self, stock, ticktime=1, pricetype=1):
        '''
        stock: name of a stock
        ticktime: one of 1, 3, 5, 10, 30
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        stockcode = self.all_stocks[stock]
        self.stockcode_non_realtime = stockcode      
        self.requesting_time_unit = str(ticktime)+'틱'
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('틱범위', ticktime)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10079', 'opt10079', 0, '0003')

        while self.remaining_data == True:
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('틱범위', ticktime)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10079', 'opt10079', 2, '0004')
    
    def request_mass_data(self, stocklist, prenext=0):
        code_list = ''
        codecnt = len(stocklist)
        for idx, stock in enumerate(stocklist):
            if idx == 0:
                code_list += self.all_stocks[stock]
            else:
                code_list += ';'+self.all_stocks[stock] #CommKwRqData() receives multiple stock tickers as one string separated with ;
        print('\n\nRequesting the real time data of the following tickers: ', code_list)
        self.comm_kw_rq_data(code_list, prenext, codecnt, typeflag=0, rqname='OPTKWFID', scrno='0005')
            
    def request_real_data(self, codelist, fidlist, opttype='1', scrno='0100'):            
        self.set_real_data(scrno, codelist, fidlist, opttype)
    
 
app = QApplication(sys.argv)

kiwoom = Kiwoom()

kiwoom.request_minute_chart('삼성전자', 30)
# kiwoom.request_mass_data('삼성전자', 'NAVER', '컬러레이', '현대차', '카카오', 'LG에너지솔루션')

# print(kiwoom.all_stocks)
