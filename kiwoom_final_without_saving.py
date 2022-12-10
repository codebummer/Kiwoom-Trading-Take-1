from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time, asyncio
import sys, os, json, logging
from datetime import datetime
# import matplotlib.pyplot as plt

#change the current working directory
# path = r'D:\myprojects\TradingDB' + '\\' + datetime.today().strftime('%Y-%m-%d')
path = r'D:\myprojects\TradingDB'
if not os.path.exists(path):
     os.mkdir(path)
os.chdir(path) 

# Create and configure logger
logging.basicConfig(filename="kiwoom_log.log", format='%(asctime)s %(message)s', filemode='w')
# Creating an object
logger = logging.getLogger()
# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)
# # Test messages
# logger.debug("Harmless debug Message")
# logger.info("Just an information")
# logger.warning("Its a Warning")
# logger.error("Did you try to divide by zero")
# logger.critical("Internet is down")


TR_REQ_TIME_INTERVAL = 0.2

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
       
        self.reset()
        self.OCX_available()      
        self._event_handlers()
        self._login()        
        self.account_info()    
        self.all_stocks = self.stock_ticker()
        self._make_timer()  

    def OCX_available(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def reset(self):
        self.account_num = 0
        self.remaining_data = True
        self.fidlist = []
        self.tr_data = {'noncharts':{}, 'charts':{}}
        self.stockcode = 0        
        self.requesting_time_unit = ''
        self.starting_time, self.lapse, self.SAVING_INTERVAL = time.time(), 0, 60*10  
        
        # tr data normally refer to the data set index of the past data, which consists of input and output names.
        # tr data can be requested by SetInputValue()/CommRqData(), and received by GetCommData() through the OnReceiveTrData() eventslot.
        # tr input names are same as the input of SetInputValue.
        # tr output names are same as the output of GetCommData().
        # i.e. 
        # tr requests: SetInputValue(tr input name, input value): set inputs. input names are '종목코드', '기준일자', '수정주가구분'...
        #                                                         input values are '005930'(for 삼성전자 종목코드), '221205'(for 기준일자)..
        #              CommRqData(...tr code...): makes a request with inputs set by SetInputValue
        # tr results: OnReceiveTrData(requestname, tr code...): receives tr code. tr codes are opt10081, opt10080, opt10079....
        #             -> GetCommData(tr code, recordname, index, tr output value): receives tr ouput names.
        #               tr ouput names are '종목코드', '현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가'....
        # fids normally refer to the indexes of the real time data, which are for output names.
        # fids are normally used in GetCommRealData(code, fid), and GetChejanData(fid) to identify requesting data.
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
                        305:'상한가', 306:'하한가'},
            '잔고' : {9201:'계좌번호', 9001:'종목코드,업종코드', 302:'종목명', 10:'현재가', 930:'보유수량', 931:'매입단가', 932:'총매입단가',
                    933:'주문가능수량', 945:'당일순매수량', 946:'매도/매수구분', 950:'당일 총 매도 손익', 951:'예수금', 27:'매도호가', 
                    28:'매수호가', 307:'기준가', 8019:'손익율', 397:'주식옵션거래단위'},
            '신용잔고' : {9201:'계좌번호', 9001:'종목코드,업종코드', 917:'신용구분', 916:'대출일', 302:'종목명', 10:'현재가', 930:'보유수량', 
                        931:'매입단가', 932:'총매입가', 933:'주문가능수량', 945:'당일순매수량', 946:'매도/매수구분', 950:'당일 총 매도 손익',
                        951:'예수금', 27:'매도호가', 28:'매수호가', 307:'기준가', 8019:'손익율', 957:'신용금액', 958:'신용이자', 918:'만기일',
                        990:'당일신현손익(유가)', 991:'당일실현손익률(유가)', 992:'당일신현손익(신용)', 993:'당일실현손익률(신용)', 959:'담보대출수량'},
            
            # Values below this line, the TR list, can be rearranged in its order
            # You can even remove FID from the values if you don't need that FID
            
            # 체결정보요청
            'opt10003' : ['시간', '현재가', '전일대비', '대비율', '우선매도호가단위', '우선매수호가단위', '체결거래량', 'sign', '누적거래량', '누적거래대금', '체결강도'],
            # 주식외국인요청
            'opt10008' : ['일자', '종가', '전일대비', '거래량', '변동수량', '보유주식수', '비중', '취득가능주식수', '외국인한도', '외국인한도증감'],
            # 가격급등락요청
            'opt10019' : ['종목코드', '종목분류', '종목명', '전일대비기호', '전일대비', '등락률', '기준가', '현재가', '기준대비', '거래량', '급등률'],
            # 일자별종목실현손익요청
            'opt10073' : ['일자', '당일hts매도수수료', '종목명', '체결량', '매입단가', '체결가', '당일매도손익', '손익율', '종목코드', '당일매매수수료', 
                          '당일매매세금', '인출가능금액', '대출일', '신용구분'],
            # 일자별실현손익요청
            'opt10074' : ['일자', '매수금액', '당일매도손익', '당일매매수수료', '당일매매세금'],
            # 당일실현손익상세요청
            'opt10077' : ['종목명', '체결량', '매입단가', '체결가', '당일매도손익', '손익율', '당일매매수수료', '당일매매세금', '종목코드'],
            # 미체결요청
            'opt10075' : ['계좌번호', '주문번호', '관리사번', '종목코드', '업무구분', '주문상태', '종목명', '주문수량', '주문가격', '미체결수량', '체결누계금액',
                          '원주문번호', '주문구분', '매매구분', '시간', '체결번호', '체결가', '체결량', '현재가', '매도호가', '매수호가', '단위체결가', '단위체결량',
                          '당일매매수수료', '당일매매세금', '개인투자자'],
            # 체결요청
            'opt10076' : ['주문번호', '종목명', '주문구분', '주문가격', '주문수량', '체결가', '체결량', '미체결량', '당일매매수수료', '당일매매세금', 
                          '주문상태', '매매구분', '원주문번호', '주문시간', '종목코드'],
            # 계좌수익율요청
            'opt10085' : ['일자', '종목코드', '종목명', '현재가', '매입가', '매입금액', '보유수량', '당일매도손익', '당일매매수수료', '당일매매세금', '신용구분', 
                          '대출일', '결제잔고', '청산가능수량', '신용금액', '신용이자', '만기일'],
            # 계좌평가현황요청
            'OPW00004' : ['종목코드', '종목명', '보유수량', '평균단가', '현재가', '평가금액', '손익금액', '손익율', '대출일', '매입금액', '결제잔고', '천일매수수량',
                          '전일매도수량', '금일매수수량', '금일매도수량'],
            # 계좌평가잔고내역요청
            'opw00018' : ['종목번호', '종목명', '평가손익', '수익률(%)', '매입가', '전일종가', '보유수량', '매매가능수량', '현재가', '전일매수수량', '전일매도수량', 
                          '금일매수수량', '금일매도수량', '매입금액', '매입수수료', '평가금액', '평가수수료', '세금', '수수료합', '보유비중(%)', '신용구분', 
                          '신용구분명', '대출일'],
            # 체결잔고요청
            'opw00005' : ['신용구분', '대출일', '만기일', '종목번호', '종목명', '결제잔고', '현재잔고', '현재가', '매입단가', '매입금액', '평가금액', '평가손익', '손익률'],
            # 예수금상세현황요청
            'opw00001' : ['통화코드', '외화예수금', '원화대용평가금', '해외주식증거금', '출금가능금액(예수금)', '주문가능금액(예수금)', '외화미수(합계)', '외화현금미수금', 
                          '연체료', 'd+1외화예수금', 'd+2외화예수금', 'd+3외화예수금', 'd+4외화예수금'],
            # 주식틱차트조회요청
            # 'opt10079' : ['현재가', '거래량', '체결시간', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분',
            #                 '종목정보', '수정주가이벤트', '전일종가'],
            'opt10079' : ['체결시간', '시가', '고가', '저가', '현재가', '거래량'],
            # 주식분봉차트조회요청
            # 'opt10080' : ['현재가', '거래량', '체결시간', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분', 
            #                 '종목정보', '수정주가이벤트', '전일종가'],
            'opt10080' : ['체결시간', '시가', '고가', '저가', '현재가', '거래량'],        
            # 주식일봉차트조회요청
            # 'opt10081' : ['종목코드', '현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분',
            #                 '소업종구분', '종목정보', '수정주가이벤트', '전일종가'],
            'opt10081' : ['일자', '시가', '고가', '저가', '현재가', '거래량', '거래대금'],            
            # 주식주봉차트조회요청
            # 'opt10082' : ['현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분', 
            #               '종목정보', '수정주가이벤트', '전일종가'],
            'opt10082' : ['일자', '시가', '고가', '저가', '현재가', '거래량', '거래대금'],
            # 주식월봉차트조회요청
            # 'opt10083' : ['현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분',
            #               '종목정보',' 수정주가이벤트', '전일종가'],
            'opt10083' : ['일자', '시가', '고가', '저가', '현재가', '거래량', '거래대금'],
            # 주식관심종목정보요청
            'OPTKWFID' : ['종목코드', '종목명', '현재가', '기준가', '전일대비', '전일대비기호', '등락율', '거래량', '거래대금', '체결량', 
                            '체결강도', '전일거래량대비', '매도호가', '매수호가', '매도1차호가', '매도2차호가', '매도3차호가', '매도4차호가',
                            '매도5차호가', '매수1차호가', '매수2차호가', '매수3차호가', '매수4차호가', '매수5차호가', '상한가', '하한가', '시가',
                            '고가', '저가', '종가', '체결시간', '예상체결가', '예상체결량', '자본금', '액면가', '시가총액', '주식수', '호가시간',
                            '일자', '우선매도잔량', '우선매수잔량', '우선매도건수', '우선매수건수', '총매도잔량', '총매수잔량', '총매도건수', 
                            '총매수건수', '패리티', '기어링', '손익분기', '자본지지', 'ELW행사가', '전환비율', 'ELW만기일', '미결제약정', '미결제전일대비',
                            '이론가', '내재변동성', '델타', '감마', '쎄타', '베가', '로'],
            
            # Do not change the following 주문메세지 unless it's absolutely necessary.
            # In case you change them, change the 'all_msg' list in '_receive_msg' to match the change in the following
            '주문메세지' : ['주문시간', '종목명', '거래코드', '메세지', '투자구분', '거래종류' ]
        }
        self.orders_dict = {
            '호가구분' : {'00':'지정가', '03':'시장가', '05':'조건부지정가', '06':'최유리지정가', '07':'최우선지정가', '10':'지정가IOC', '13':'시장가IOC', 
                        '16':'최유리IOC', '20':'지정가FOK', '23':'시장가FOK', '26':'최유리FOK', '61':'장전시간외종가', '62':'시간외단일가매매', '81':'장후시간외종가'},
            '주문리턴' : {0:'주문성공', -308:'1초5회이상주문에러'}
        }
        self.charts = {'월봉':'opt10083', '주봉':'opt10082', '일봉':'opt10081', '분봉':'opt10080', '틱':'opt10079'}          
      
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

    def _make_timer(self):
        # QTimer() should be instantiated before _time_event_handler or it will cause an error
        self.savetimer = QTimer() 
        self.timer_count = 0
        self._time_event_handler()
        self.timeset()
    
    def _time_event_handler(self):
        self.savetimer.timeout.connect(self._timer_refresh_data)
    
    def timeset(self, minute_interval=3):
        # millisec_interval = minute_interval * 60_000
        # millisec_interval = 0.01 * 60_000
        millisec_interval = 1 * 60_000
        self.savetimer.setInterval(millisec_interval)
        self.savetimer.start()
        print(f'Auto chart data requesting interval is set for {minute_interval} minute(s)')        
        print(f'Autosaving interval is set for {minute_interval*20} minute(s)')       

    def _timer_refresh_data(self):
        self.timer_count += 1
        stock = self.all_stocks['tickerkeys'][self.stockcode]

        for df_name in self.tr_data['charts'].keys():
            if '3분' in df_name and stock in df_name:
                # print('df_name, self.tr_data[charts][df_name]: <- in _timer_refresh_data ', df_name, '\n', self.tr_data['charts'][df_name])
                self.tr_data['charts'].pop(df_name)
                break
        
        # print('requesting 3min charts <- _timer_refresh_data')
        # print('stock, df_name, self.tr_data[charts].keys() in _timer_refresh_data: ', stock, df_name,'<->', self.tr_data['charts'].keys())        
        
        # df_name should be input to self._apply_strategies as a list form.
        # self.min3() returns df_name as a string, 'return stock+realtype+self.requesting_time_unit',
        # which means df_name here below have to be in a list form.
        # However, this is done by the last line of this method.
        # self._apply_strategies(df_name.values())       
        df_name = {}
        df_name['3분봉'] = self.min3(stock)
 
        if (self.timer_count*3 % 30) == 0:
            for df_name in self.tr_data['charts'].keys():
                if '30분' in df_name and stock in df_name:
                    self.tr_data['charts'].pop(df_name)
                    break
            df_name['30분봉'] = self.min30(stock)

        if (self.timer_count*3 % 60) == 0:
            for df_name in self.tr_data['charts'].keys():
                if '60분' in df_name and stock in df_name:
                    self.tr_data['charts'].pop(df_name)
                    break
            df_name['60분봉'] = self.min60(stock)
            
            self._timersave_df
        # multiple timers can be activated simulanteously, 
        # which is why _apply_strategies is at the bottom line of this method
        # to reflect all the possible changes at once.
        self._apply_strategies(df_name.values())
   

    def _timersave_df(self):
        print('\nAutosaving in progress...')
        for df_name, df in self.tr_data['noncharts'].items():       
            # The following statement makes db file names in _data_to_sql, which is different from df_name
            # df_name is same as tr_data['charts] or tr_data['noncharts'] keys, which is done in _df_generator
            if '일자' in df.columns():
                self._data_to_sql(df_name, df_name+'.db', df)
            else:
                self._data_to_sql(df_name+'_'+datetime.today().strftime('%Y년%m월%d일'), df_name+'.db', df)
            print(f'{df_name} is saved in {df_name}.db')            
        self.tr_data['noncharts'] = {}        
        minute_interval = int(self.savetimer.interval()/60_000)
        print(f'\nAutosaving for every {minute_interval} minute completed.')
        
    def data_from_sql(self, tablename, filename):
        with sqlite3.connect(filename) as file:
            return pd.read_sql(f'SELECT * FROM [{tablename}]', file)    
    
    def _data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')
                
    #type == 1: db is a filename, type == 0: db is a db handle or db sqlite3 connect pointer                 
    def _get_db_info(self, db, type):
        '''
        db: a file name or a sqlite3 connec pointer. 
        type: 
        0: db is a sqlite3 connect pointer or handle 1: db is a filename         
        returns 
        tablenames: a tuple
        columnnames: a pandas.Series'''
        if db: #db is a filename                        
            with sqlite3.connect(db) as file:
                query = '''SELECT name FROM sqlite_master WHERE type='table';'''
                tablenames = file.cursor().execute(query).fetchall()[0]
                columnnames = pd.read_sql(f'PRAGMA TABLE_INFO({tablenames[-1]})', file).name
        else: #db is a db handle or db sqlite3 connect pointer
            query = '''SELECT name FROM sqlite_master WHERE type='table';'''
            tablenames = db.cursor().execute(query).fetchall()[0]
            columnnames = pd.read_sql(f'PRAGMA TABLE_INFO({tablenames[-1]})', db).name            
        return tablenames, columnnames      
            
    def _df_generator(self, realtype, data):   
        '''
        realtype: 주식시세, 주식체결, 주문체결, 체결잔고, 잔고변경, 주문메세지, 주식일봉차트, 주식틱차트, 관심종목
        data: dataframe which contains data to save
        '''        
        # (stock name +) realtype (+ a time unit) = df_name = tr_data['charts'] or tr['noncharts'] keys
        # 체결잔고, 잔고변경, 주문메세지 will each have one same filename with multiple table names for additional data to save
        # They also have df_name in the form of : realtype

        # if realtype in ['체결잔고', '잔고변경', '주문메세지', '관심종목']:        
        #     df_name = realtype

        # 주식시세, 주식체결, 주문체결, 주식일봉차트, 주식틱차트, 관심종목 will have df_name consising of
        # stock_realtype_timeunit : i.e. 삼성전자_주식일봉차트_30분봉
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        if realtype in ['주식분봉차트', '주식틱차트']:    
            # df_name is same as tr_datakeys, which is done in _df_generator
            # db file names are differently named in _data_to_sql, which is done in _timersave_df  
            df_name = stock+'_'+realtype+'_'+self.requesting_time_unit
            if df_name in self.tr_data['charts'].keys():
                self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['charts'][df_name] = pd.DataFrame(data)

        elif realtype in ['주식일봉차트', '주식주봉차트', '주식월봉차트']:
            df_name = stock+'_'+realtype
            if df_name in self.tr_data['charts'].keys():
                self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['charts'][df_name] = pd.DataFrame(data)
        else:
            df_name = realtype
            if df_name in self.tr_data['noncharts'].keys():
                self.tr_data['noncharts'][df_name] = self.tr_data['noncharts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['noncharts'][df_name] = pd.DataFrame(data)
        return df_name
          
    def account_info(self):
        #GetLoginInfo() takes its argument as a list form. Put all the input values in []
        self.account_num = self.dynamicCall('GetLoginInfo(QString)', ['ACCNO']).strip(';')
        # print(self.account_num)

    def stock_ticker(self):
        #GetCodeListByMarket() takes its argument as a list form. Put all the input values in []
        response = self.dynamicCall('GetCodeListByMarket(QString)', ['']) # '' means all markets. '0' means KOSPI. '10' means KOSDAQ.
        tickers = response.split(';')
        stock_list = {'tickerkeys':{}, 'stockkeys':{}}
        for ticker in tickers:
            if ticker == '':
                continue
            else:
                stock = self.dynamicCall('GetMasterCodeName(QString)', [ticker])
                stock_list['tickerkeys'][ticker] = stock
                stock_list['stockkeys'][stock] = ticker
        with open('stocklist.json', 'w') as file:
            json.dump(stock_list, file)
        with open('tickers.txt', 'w') as file:
            file.write(str(list(stock_list['tickerkeys'].keys())))
        print('\nSaved Stock List in stocklist.json file and Ticker List in tickers.txt')
        return stock_list
    
    def set_input_value(self, tr_name, tr_value):
        self.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
    
    def set_real_data(self, scrno, codelist, fidlist, opttype):
        for idx, code in enumerate(codelist):
            print(f'\n\nrequesting data of {code}')
            self.dynamicCall('SetRealReg(QString, QString, QString, QString)', f'00{idx+100}', code, fidlist, opttype)
                
        self._event_loop_exec('real')
        
    def set_order(self, rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno):
        #SendOrder() takes its argument as a list form. Put all the input values in []
        self.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', [rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno])
        
        self._event_loop_exec('order')
    
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
        '''
        rqname : OPT10080, OPT10081... useder defined distinguishers
        trcode : opt10080, opt10081... API given distinguishers
        '''        
        # if prenext == 2:
        #     self.remaining_data = True
        # elif prenext == 0:
        #     self.remaining_data = False
            
        # print('scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4: ->in _receive_tr_data\n',\
        #         scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4)        

        # 주식틱차트조회요청
        if rqname == 'OPT10079':
            self._opt10079(rqname, trcode)
        # 주식분봉차트조회요청
        elif rqname == 'OPT10080':
            self._opt10080(rqname, trcode)
        # 주식일봉차트조회요청
        elif rqname == 'OPT10081':
            self._opt10081(rqname, trcode)
        # 주식주봉차트조회요청
        elif rqname == 'OPT10082':
            self._opt10082(rqname, trcode)
        # 주식월봉차트조회요청
        elif rqname == 'OPT10083':
            self._opt10083(rqname, trcode)
        # 주식관심종목정보요청
        elif rqname == 'OPTKWFID':
            self._optkwfid(rqname, trcode)

       
        # 계좌평가잔고내역요청
        elif rqname == 'OPW00018':
            self._opw00018(rqname, trcode)
        # 예수금상세현황요청
        elif rqname == 'OPW00001':
            self._opw00001(rqname, trcode)
        # 계좌수익율요청
        elif rqname == 'OPT10085':
            self._opt10085(rqname, trcode)
        # 당일실현손익상세요청    
        elif rqname == 'OPT10077':
            self._opt10077(rqname, trcode)
        # 체결요청
        elif rqname == 'OPT10076':
            self._opt10076(rqname, trcode)
        # 미체결요청
        elif rqname == 'OPT10075':
            self._opt10075(rqname, trcode)
        

        '''
        IMPORTANT 
        The following 4 lines to exit the EVENT LOOP should be ON to request continuous data.
        However, in case you only want a single request with a time interval, 
        the EVENT LOOP should be OFF, 
        or the program will be terminated without keeping connected to the server.
        '''
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
        
        try:
            self._event_loop_exit('real')
        except AttributeError:
            pass
    
    def _receive_msg(self, scrno, rqname, trcode, msg):
        # print('\n\nscrno, rqname, trcode, msg: ->in _receive_msg\n', scrno, rqname, trcode, msg)
        add = {}
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        msg_trimmed = msg.split()
        msg_trimmed[0] = msg_trimmed[0].strip('[]')
        all_msg = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), stock, trcode, msg_trimmed[0], msg_trimmed[1], msg_trimmed[2]]
        print(all_msg[0], all_msg[1], all_msg[4], all_msg[5])
        for idx, key in enumerate(self.fids_dict['주문메세지']):
            add[key] = [all_msg[idx]]
        self._df_generator('주문메세지', add)

    def _receive_chejan_data(self, gubun, itemcnt, fidlist): 
        '''
        itemcnt in _receive_chejan_data is the number of fid elements in fidlist
        fidlist is received in the form of a one long string connected by ;
        fidlist example : 9201;9203;9205;9001;912;913;302;900;901;902;903;904;905;906;907;908;909;910
        itemcnt for the above fidlist exmaple will be its number, 18    
        '''   
        # print('gubun, type(gubun): -> in _receive_chejan_data\n', gubun, type(gubun))
        if gubun == '0': #order placed and made 
            self._real_chejan_placed_made(itemcnt, fidlist)
        elif gubun == '1':
            self._domestic_balance_change(itemcnt, fidlist)
        
        try:
            self._event_loop_exit('order')
        except AttributeError:
            pass

    def _real_chejan_placed_made(self, itemcnt, fidlist): #itemcnt is the number of fid elements in fidlist
        # print('\nitemcnt, fidlist: -> in_real_chejan_placed_made\n', itemcnt, fidlist)
        print('order placed and made')
        fidlist = fidlist.split(';')
        fidlist_checked = []
        fid_indict = [str(key) for key in self.fids_dict['주문체결'].keys()]
        for fid in fidlist:
            if fid in fid_indict:
                fidlist_checked.append(fid)
        add = {}
        for fid in fidlist_checked:
            add[self.fids_dict['주문체결'][int(fid)]] = [self._get_chejan_data(fid)]
        #the second argument, stockcode, is assigned '', 
        #which makes _df_generator df_name without stock name in it.
        df_name, df = self._df_generator('체결잔고', add)
        print(df)

    def _domestic_balance_change(self, itemcnt, fidlist): #itemcnt is the number of fid elements in fidlist
        # print('\nitemcnt, fidlist: -> in _domestic_balance_chanage\n', itemcnt, fidlist)
        print('change in balance happened')
        fidlist = fidlist.split(';')
        fidlist_checked = []
        fid_indict = [str(key) for key in self.fids_dict['신용잔고'].keys()]
        for fid in fidlist:
            if fid in fid_indict:
                fidlist_checked.append(fid)
        add = {}
        for fid in fidlist_checked:
            add[self.fids_dict['신용잔고'][int(fid)]] = [self._get_chejan_data(fid)]
        df_name, df = self._df_generator('잔고변경', add) 
        print(df)
    
    def _realtype_stock_status(self, code):
        add= {}
        fidlist = self.fids_dict['주식시세']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.stockcode = code
        df_name, df = self._df_generator('주식시세', add)
        print(df)

    def _realtype_stock_made(self, code): 
        add= {}
        fidlist = self.fids_dict['주식체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.stockcode = code       
        df_name, df = self._df_generator('주식체결', add)
        print(df)
 
    def _realtype_order_made(self, code):
        add= {}
        fidlist = self.fids_dict['주문체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]

        self.stockcode = code        
        df_name, df = self._df_generator('주문체결', add)   
        print(df)
    
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_chejan_data(self, fid):
        return self.dynamicCall('GetChejanData(int)', fid)

    def _get_repeat_cont(self, trcode, recordname):   
        # print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()
    
    # _opt10079 ~ _opt10081 have an item for stock codes in output values in the guidebook, 
    # but actually return blank instead of stock codes 
    
    # 주식틱차트조회요청 결과처리
    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')        
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10079']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            self._df_generator('주식틱차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} {self.requesting_time_unit}틱차트 정보 {data_cnt}건 수신')         
        
    # 주식분봉차트조회요청 결과처리
    def _opt10080(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식분봉차트')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10080']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            df_name = self._df_generator('주식분봉차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} {self.requesting_time_unit}분봉차트 정보 {data_cnt}건 수신')    
        # print(self.tr_data['charts'][df_name])
        
    # 주식일봉차트조회요청 결과처리
    def _opt10081(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10081']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            df_name = self._df_generator('주식일봉차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 일봉차트 정보 {data_cnt}건 수신')
        # print(self.tr_data['charts'][df_name])

    
    # 주식주봉차트조회요청 결과처리
    def _opt10082(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식주봉차트')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10082']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('주식주봉차트', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 주봉차트 정보 {data_cnt}건 수신')    
    
    # 주식월봉차트조회요청 결과처리
    def _opt10083(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식월봉차트')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10083']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('주식월봉차트', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 월봉차트 정보 {data_cnt}건 수신')                
    
    # _optkfid is actually for simultaneous multiple stock data requests, not 관심종목
    # This actually returns stock codes in its output values
    def _optkwfid(self, rqname, trcode):    
        data_cnt = self._get_repeat_cont(trcode, '관심종목')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['OPTKWFID']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self.stockcode = add['종목코드'][0]
            self._df_generator('관심종목', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 관심종목 정보 {data_cnt}건 수신')  

    # 계좌평가잔고내역요청
    def _opw00018(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '계좌평가잔고내역')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw00018']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('계좌평가잔고내역', add)
        print(f'계좌평가잔고내역 수신\n', self.tr_data['noncharts']['계좌평가잔고내역'])    
    
    # 예수금상세현황요청
    def _opw00001(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '예수금상세현황')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw00001']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('예수금상세현황', add)
        print(f'예수금상세현황 수신\n', self.tr_data['noncharts']['예수금상세현황'])  
    
    # 계좌수익율요청
    def _opt10085(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '계좌수익율')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10085']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('계좌수익율', add)
        print(f'계좌수익율 수신\n', self.tr_data['noncharts']['계좌수익율'])        

    # 당일실현손익상세요청
    def _opt10077(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '당일실현손익상세')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw10077']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('당일실현손익상세', add)
        print(f'당일실현손익상세 수신\n', self.tr_data['noncharts']['당일실현손익상세'])      

    # 체결요청
    def _opt10076(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '체결')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw10076']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('체결', add)
        print(f'체결 수신\n', self.tr_data['charts']['체결'])      

    # 미체결요청
    def _opt10075(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '미체결')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw10075']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('미체결', add)
        print(f'미체결 수신\n', self.tr_data['noncharts']['미체결'])      
    
    # The following methods preprocess received data from the server and generate data for strategies
    def _floatize_df(self, df_name):
        '''df_name should be one string'''
        # print('df_name,  self.tr_data[charts][df_name].columns: in _floatize_df: ', df_name, self.tr_data['charts'][df_name].columns)
        self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].astype('string')
        for column in self.tr_data['charts'][df_name].columns:
            self.tr_data['charts'][df_name][column] = self.tr_data['charts'][df_name][column].str.strip('+-')
        self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].astype('float')
    
    def _mas(self, df_name):
        '''df_name should be one string'''
        ma_types = {'MA240':240, 'MA120':120, 'MA60':60, 'MA20':20, 'MA10':10, 'MA5':5, 'MA3':3}
        self.tr_data['charts'][df_name]['거래량변화율'] = self.tr_data['charts'][df_name]['거래량'].pct_change(1)
        for ma, term in ma_types.items():
            self.tr_data['charts'][df_name][ma] = self.tr_data['charts'][df_name]['현재가'].rolling(window=term).mean()

    def _bollinger(self, df_name):
        '''df_name should be one string'''
        if 'MA20' not in self.tr_data['charts'][df_name].columns:
            self.tr_data['charts'][df_name]['MA20'] = self.tr_data['charts'][df_name]['현재가'].rolling(window=20).mean()
        self.tr_data['charts'][df_name]['STD'] = self.tr_data['charts'][df_name]['현재가'].rolling(window=20).std()
        self.tr_data['charts'][df_name]['Upper'] = self.tr_data['charts'][df_name]['MA20'] + 2 * self.tr_data['charts'][df_name]['STD']
        self.tr_data['charts'][df_name]['Lower'] = self.tr_data['charts'][df_name]['MA20'] - 2 * self.tr_data['charts'][df_name]['STD']
        self.tr_data['charts'][df_name]['PB'] = (self.tr_data['charts'][df_name]['현재가'] - self.tr_data['charts'][df_name]['저가']) / (self.tr_data['charts'][df_name]['Upper'] - self.tr_data['charts'][df_name]['Lower'])
        self.tr_data['charts'][df_name]['Bandwidth'] = (self.tr_data['charts'][df_name]['현재가'] - self.tr_data['charts'][df_name]['저가']) / self.tr_data['charts'][df_name]['MA20'] * 100
        self.tr_data['charts'][df_name]['SQZ'] = (self.tr_data['charts'][df_name]['Upper'] - self.tr_data['charts'][df_name]['Lower']) / self.tr_data['charts'][df_name]['MA20'] * 100
    
    def _RSI(self, df_name):
        '''df_name should be one string'''
        self.tr_data['charts'][df_name]['Diff'] = self.tr_data['charts'][df_name]['현재가'].diff(1)
        self.tr_data['charts'][df_name]['Gain'] = self.tr_data['charts'][df_name]['Diff'].clip(lower=0).round(2)
        self.tr_data['charts'][df_name]['Loss'] = self.tr_data['charts'][df_name]['Diff'].clip(upper=0).abs().round(2)
        self.tr_data['charts'][df_name]['AvgGain'] = self.tr_data['charts'][df_name]['Gain'].rolling(window=10).mean()
        self.tr_data['charts'][df_name]['AvgLoss'] = self.tr_data['charts'][df_name]['Loss'].rolling(window=10).mean()
        self.tr_data['charts'][df_name]['RSI'] = 100 - 100 / (1 + self.tr_data['charts'][df_name]['AvgGain'] / self.tr_data['charts'][df_name]['AvgLoss'])

    def _MFI(self, df_name):
        '''df_name should be in one string'''
        self.tr_data['charts'][df_name]['TP'] = (self.tr_data['charts'][df_name]['고가'] + self.tr_data['charts'][df_name]['저가'] + self.tr_data['charts'][df_name]['현재가']) / 3
        self.tr_data['charts'][df_name]['PMF'] = 0
        self.tr_data['charts'][df_name]['NMF'] = 0
        for idx in range(len(self.tr_data['charts'][df_name])-1):
            if self.tr_data['charts'][df_name]['TP'].values[idx] < self.tr_data['charts'][df_name]['TP'].values[idx+1]:
                self.tr_data['charts'][df_name]['PMF'].values[idx+1] = self.tr_data['charts'][df_name]['TP'].values[idx+1] * self.tr_data['charts'][df_name]['거래량'].values[idx+1]
                self.tr_data['charts'][df_name]['NMF'] = 0
            else:
                self.tr_data['charts'][df_name]['NMF'].values[idx+1] = self.tr_data['charts'][df_name]['TP'].values[idx+1] * self.tr_data['charts'][df_name]['거래량'].values[idx+1]
                self.tr_data['charts'][df_name]['PMF'] = 0
        self.tr_data['charts'][df_name]['MFR'] = self.tr_data['charts'][df_name]['PMF'].rolling(window=10).sum() / self.tr_data['charts'][df_name]['NMF'].rolling(window=10).sum()
        self.tr_data['charts'][df_name]['MFR10'] = 100 - 100 / (1 + self.tr_data['charts'][df_name]['MFR'])
    
    def _stochastic(self, df_name):
        '''df_name should be in one string'''
        k = 14
        d = 3
        self.tr_data['charts'][df_name]['K고가'] = self.tr_data['charts'][df_name]['고가'].rolling(k).max()
        self.tr_data['charts'][df_name]['K저가'] = self.tr_data['charts'][df_name]['저가'].rolling(k).min()
        self.tr_data['charts'][df_name]['%K'] = (self.tr_data['charts'][df_name]['현재가'] - self.tr_data['charts'][df_name]['K저가']) * 100 / (self.tr_data['charts'][df_name]['K고가'] - self.tr_data['charts'][df_name]['K저가'])
        self.tr_data['charts'][df_name]['%D'] = self.tr_data['charts'][df_name]['%K'].rolling(d).mean()      

      
    # *inputs take multiple functions to use and a list form of input values in order.
    # The functions will be inputs[:-1] and input values will be imputs[-1]
    def _apply_strategies(self, df_names):
        '''df_names should be in a list form'''
        def _fmap(*inputs):
            '''*inputs should be functions first and values last. And the values should be in a list form'''
            for func in inputs[:-1]:
                for input in inputs[-1]:
                    func(input)
        _fmap(self._floatize_df, self._mas, self._bollinger, self._RSI, self._MFI, self._stochastic, df_names)
        
    
    def _chart_request(self, stock, date_or_tick, pricetype=1):
        stockcode = self.all_stocks['stockkeys'][stock]
        self.stockcode = stockcode  
        self.set_input_value('종목코드', stockcode)        

        if self.requesting_time_unit in ['월봉', '주봉', '일봉']:
            trcode = self.charts[self.requesting_time_unit]
            self.set_input_value('기준일자', date_or_tick)
            self.set_input_value('수정주가구분', pricetype)
            # upper case of trcode = rqname
            self.comm_rq_data(str.upper(trcode), trcode, 0, '0001')            
            date_edited = date_or_tick[:4]+'년'+date_or_tick[4:6]+'월'+date_or_tick[6:]+'일'
        elif '분' in self.requesting_time_unit or '틱' in self.requesting_time_unit:
            timeunit = '분봉' if '분' in self.requesting_time_unit else '틱'
            trcode = self.charts[timeunit]
            self.set_input_value('틱범위', date_or_tick)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data(str.upper(trcode), trcode, 0, '0001')
            date_edited = datetime.now().strftime('%Y-%m-%d %H:%M:%S')            
        # The following message is commented out,
        # because data can be received before the message can be printed, 
        # resulting in printing '수신완료' messages first and '요청' messages later
        # print(f'{stock} {date_edited}부터 {self.requesting_time_unit}차트 요청')         

        # while self.remaining_data == True:
        #     time.sleep(TR_REQ_TIME_INTERVAL)
        #     self.set_input_value('종목코드', stockcode)
        #     self.set_input_value('기준일자', date)
        #     self.set_input_value('수정주가구분', pricetype)
        #     self.comm_rq_data('OPT10081', 'opt10081', 2, '0002')
    
    def request_monthly_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '월봉'
        self._chart_request(stock, date, pricetype)
       
    def request_weekly_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '주봉'
        self._chart_request(stock, date, pricetype)
      
    def request_daily_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '일봉'
        self._chart_request(stock, date, pricetype)

    def request_minute_chart(self, stock, mintime=30, pricetype=1):
        '''
        stock: name of a stock
        mintime: one of 1, 3, 5, 10, 15, 30, 45, 60 
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''   
        self.requesting_time_unit = str(mintime)+'분'
        self._chart_request(stock, mintime, pricetype)
    
    def request_tick_chart(self, stock, ticktime=1, pricetype=1):
        '''
        stock: name of a stock
        ticktime: one of 1, 3, 5, 10, 30
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''  
        self.requesting_time_unit = str(ticktime)+'틱'
        self._chart_request(stock, ticktime, pricetype)
    
    # Simplified chart request functions. Return df_name
    def min3(self, stock):
        self.request_minute_chart(stock, 3, pricetype=1)
        return stock+'_'+'주식분봉차트'+'_'+self.requesting_time_unit
    def min10(self, stock):
        self.request_minute_chart(stock, 10, pricetype=1)
        return stock+'_'+'주식분봉차트'+'_'+self.requesting_time_unit
    def min30(self, stock):
        self.request_minute_chart(stock, 30, pricetype=1)
        return stock+'_'+'주식분봉차트'+'_'+self.requesting_time_unit
    def min60(self, stock):
        self.request_minute_chart(stock, 60, pricetype=1)
        return stock+'_'+'주식분봉차트'+'_'+self.requesting_time_unit
    def daily(self, stock):
        self.request_daily_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
        return stock+'_'+'주식일봉차트'
    def weekly(self, stock):
        self.request_weekly_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
        return stock+'_'+'주식주봉차트'        
    def monthly(self, stock):
        self.request_monthly_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
        return stock+'_'+'주식월봉차트'
    
    def onestop_stock(self, stock):
        df_name_collect = {'3분봉':self.min3, '10분봉':self.min10, '30분봉':self.min30, '60분봉':self.min60, 
                         '일봉':self.daily, '주봉':self.weekly, '월봉':self.monthly}
        df_names = {}
        # chart_func below will return df_name
        for df_key, chart_func in df_name_collect.items():
            df_names[df_key] = chart_func(stock)

        self._apply_strategies(df_names.values())
        
        # for df_name, df in self.tr_data['charts'].items():
        #     with sqlite3.connect('chart_test.db') as file:
        #         df.to_sql(df_name, file, if_exists='append')

        
    def request_mass_data(self, *stocklist, prenext=0):
        code_list = ''
        stocks = [] 
        self.requesting_time_unit = '1틱'
        
        if type(stocklist) == list:
            if type(stocklist[0]) == str and len(stocklist) == 1:
                stocklist = stocklist[0]
                
            #when stocklist is a list filled with strings. stocklist=['삼성전자', '현대차']
            elif type(stocklist[0]) == str and len(stocklist) > 1:
                pass
            
        #when one list filled with stock name strings, it will actually be a list covered with a tuple
        #request_mass_data(stocks[:100]) -> stocks[:100] is in the form of ['삼성전자', '현대차']
        #the stocklist argument gets that input in the form of (['삼성전자', '현대차'])
        elif type(stocklist) == tuple and type(stocklist[0]) == list and type(stocklist[0][0] == str) and len(stocklist[0]) > 1:
            stocklist = stocklist[0][0]
        
        elif type(stocklist) == tuple and type(stocklist[0]) == str and len(stocklist) == 1:
            stocklist = stocklist[0]
        #when stocklist is a long string with stock names separated with ,
        #'삼성전자, 현대차, LG전자'
        elif type(stocklist) == str:
            pass

        for stock in stocklist.split(','):
            stocks.append(stock.strip())

        print(f'{stocklist} 1틱차트 실시간 정보 요청')
 
        codecnt = len(stocks)
        for idx, stock in enumerate(stocks):      
            if idx == 0:
                code_list += self.all_stocks['stockkeys'][stock]
            else:
                code_list += ';'+self.all_stocks['stockkeys'][stock] #CommKwRqData() receives multiple stock tickers as one string separated with ;
        # print('\n\nRequesting the real time data of the following tickers: ', code_list)
        self.comm_kw_rq_data(code_list, prenext, codecnt, typeflag=0, rqname='OPTKWFID', scrno='0005')
            
    def request_real_data(self, codelist, fidlist, opttype='1', scrno='0100'):            
        self.set_real_data(scrno, codelist, fidlist, opttype)
    
    def make_order(self, stock, price, qty, hogagb='00', ordertype=1, orderno=' '):
        '''
        stock: 주식이름
        price: 주문가격
        qty: 주문수량
        hogagb: 거래구분(혹은 호가구분)        
            '00':'지정가', '03':'시장가', '05':'조건부지정가', '06':'최유리지정가', '07':'최우선지정가', '10':'지정가IOC', '13':'시장가IOC',
            '16':'최유리IOC', '20':'지정가FOK', '23':'시장가FOK', '26':'최유리FOK', '61':'장전시간외종가', '62':'시간외단일가매매', '81':'장후시간외종가'
        ordertype: 주문유형 1:신규매수(default), 2:신규매도 3:매수취소, 4:매도취소, 5:매수정정, 6:매도정정      
        orderno: 원주문번호. 신규주문에는 공백 입력, 정정/취소시 입력합니다.        
        '''
        stockcode = self.all_stocks['stockkeys'][stock]
        self.stockcode = stockcode
        order = ['신규매수', '신규매도', '매수취소', '매도취소', '매수정정', '매도정정'][ordertype]
        # print('\nself.account_num, ordertype, stockcode, qty, price, hogagb, orderno:\n', self.account_num, ordertype, stockcode, qty, price, hogagb, orderno)
        print(f'{stock} {price}원 {qty}주 {order} 신청')
        self.set_order('testuser', '0006', self.account_num, ordertype, stockcode, qty, price, hogagb, orderno)
 
                        
app = QApplication(sys.argv)

kiwoom = Kiwoom()

type(kiwoom.account_num)

# if you want, set timer interval (minutes) for autosaving. Default interval is set to 5 minutes.
# kiwoom.timeset(1)
# print(kiwoom.all_stocks)
# kiwoom.make_order('삼성전자', 61100, 1, '03', 2)
buy = lambda stock, price, qty: kiwoom.make_order(stock, price, qty, '00')
sell = lambda stock, price, qty: kiwoom.make_order(stock, price, qty, '00', 2)
buyfast = lambda stock, price, qty: kiwoom.make_order(stock, price, qty, '03')
sellfast = lambda stock, price, qty: kiwoom.make_order(stock, price, qty, '03', 2)
daily = lambda stock, date=datetime.today().strftime('%Y%m%d'): kiwoom.request_daily_chart(stock, date)
min60 = lambda stock: kiwoom.request_minute_chart(stock, 60)
min30 = lambda stock: kiwoom.request_minute_chart(stock, 30)
min10 = lambda stock: kiwoom.request_minute_chart(stock, 10)
min3 = lambda stock: kiwoom.request_minute_chart(stock, 3)
tick = lambda stock: kiwoom.request_tick_chart(stock, 1)
mass = lambda stocks: kiwoom.request_mass_data(stocks)
# buy('삼성전자', 61000, 1)
# sell('삼성전자', 62000, 1)
# buyfast('삼성전자', 61000, 1)
# sellfast('삼성전자', 62000, 1)
# tick('컬러레이')
# tick('삼성전자')
# min30('삼성전자')
# min10('삼성전자')
# daily('삼성전자')
# min3('삼성전자')
kiwoom.onestop_stock('삼성전자')
# mass('LG에너지솔루션, SK텔레콤, 현대차')
