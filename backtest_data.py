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

    def OCX_available(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def reset(self):
        self.account_num = 0
        self.remaining_data = True
        self.fidlist = []
        self.tr_data = {'noncharts':{}, 'volitility':{}, 'realcharts':{}, 'charts':{}}
        self.stockcode = 0
        self.following_stocks = set()
        self.requesting_time_unit = ''
        self.df_names = {}
        self.starting_time, self.lapse, self.SAVING_INTERVAL = time.time(), 0, 60*10      
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
            # 가격급등락요청
            'opt10019' : ['종목코드', '종목분류', '종목명', '전일대비기호', '전일대비', '등락률', '기준가', '현재가', '기준대비', '거래량', '급등률'],
            # 거래량급증요청
            'OPT10023' : ['종목코드', '종목명', '현재가', '전일대비기호', '전일대비', '등락률', '이전거래량', '현재거래량', '급증률'],
            # 매물대집중요청
            'OPT10025' : ['종목코드', '종목명', '현재가', '전일대비기호', '전일대비', '등락률', '현재거래량', '가격대시작', '가격대끝', '매물량', '매물비']
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
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        if realtype in ['주식분봉차트', '주식틱차트']:    
            df_name = stock+'_'+realtype+'_'+self.requesting_time_unit
            if df_name in self.tr_data['charts'].keys():
                self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['charts'][df_name] = pd.DataFrame(data)
                
        # 주식일봉차트, 주식주봉차트, 주식월봉차트 are non real time data
        elif realtype in ['주식일봉차트', '주식주봉차트', '주식월봉차트']:
            df_name = stock+'_'+realtype
            if df_name in self.tr_data['charts'].keys():
                self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['charts'][df_name] = pd.DataFrame(data)        
                
        # 주식체결, 주식시세 are real time data.         
        elif realtype in ['주식체결', '주식시세']:
            df_name = stock+'_'+realtype
            if df_name in self.tr_data['realcharts'].keys():
                self.tr_data['realcharts'][df_name] = self.tr_data['realcharts'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['realcharts'][df_name] = pd.DataFrame(data)    

        # '가격급등락', '거래량급증', '매물대집중' are real time data.                       
        elif realtype in ['가격급등락', '거래량급증', '매물대집중']:
            df_name = realtype
            if df_name in self.tr_data['volitility'].keys():
                self.tr_data['volitility'][df_name] = self.tr_data['volitility'][df_name].append(pd.DataFrame(data), ignore_index=True)
            else:
                self.tr_data['volitility'][df_name] = pd.DataFrame(data)            
  
        # 주문체결, 잔고변경, 체결잔고 are most typical data for this category
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

    
    def comm_rq_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRQData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self._event_loop_exec('tr')
        

    def _event_loop_exec(self, loopname):
        exec(f'self.{loopname} = QEventLoop()')
        exec(f'self.{loopname}.exec_()')
    
    def _event_loop_exit(self, loopname):
        exec(f'self.{loopname}.exit()')
    
    def _receive_tr_data(self, scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4):  
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
        
        # 가격급등락요청
        elif rqname == 'OPT10019':
            self._opt10019(rqname, trcode)
        #거래량급증요청
        elif rqname == 'OPT10023':
            self._opt10023(rqname, trcode)
        #매물대집중요청
        elif rqname == 'OPT10025':
            self._opt10025(rqname, trcode)

        try:
            self._event_loop_exit('tr')            
        except AttributeError:
            pass

    def _get_repeat_cont(self, trcode, recordname):   
        # print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()

    # 주식틱차트조회요청 결과처리
    def _opt10079(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')        
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10079']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            df_name = self._df_generator('주식틱차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} {self.requesting_time_unit}틱차트 정보 {data_cnt}건 수신')
        
    # 주식분봉차트조회요청 결과처리
    def _opt10080(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식분봉차트')
        self.stockcode = self._get_comm_data(trcode, rqname, 0, '종목코드')
        add = {}        
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10080']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            df_name = self._df_generator('주식분봉차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} {self.requesting_time_unit}분봉차트 정보 {data_cnt}건 수신') 
        
    # 주식일봉차트조회요청 결과처리
    def _opt10081(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')
        self.stockcode = self._get_comm_data(trcode, rqname, 0, '종목코드')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10081']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            df_name = self._df_generator('주식일봉차트', add)   
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 일봉차트 정보 {data_cnt}건 수신')
    
    # 주식주봉차트조회요청 결과처리
    def _opt10082(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식주봉차트')
        self.stockcode = self._get_comm_data(trcode, rqname, 0, '종목코드')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10082']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            df_name = self._df_generator('주식주봉차트', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 주봉차트 정보 {data_cnt}건 수신')
    
    # 주식월봉차트조회요청 결과처리
    def _opt10083(self, rqname, trcode):
        df_name = ''
        data_cnt = self._get_repeat_cont(trcode, '주식월봉차트')
        self.stockcode = self._get_comm_data(trcode, rqname, 0, '종목코드')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10083']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            df_name = self._df_generator('주식월봉차트', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 월봉차트 정보 {data_cnt}건 수신')

    # 가격급등락요청 결과처리
    def _opt10019(self, rqname, trcode):
        df_name = ''    
        data_cnt = self._get_repeat_cont(trcode, '가격급등락')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10019']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self.stockcode = add['종목코드'][0]
            df_name = self._df_generator('가격급등락', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'가격급등락 정보 {data_cnt}건 수신')  
    
    # 거래량급증요청 결과처리
    def _opt10023(self, rqname, trcode):
        df_name = ''    
        data_cnt = self._get_repeat_cont(trcode, '거래량급증')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['OPT10023']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self.stockcode = add['종목코드'][0]
            df_name = self._df_generator('거래량급증', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'거래량급증 정보 {data_cnt}건 수신')  
    
    # 매물대집중요청 결과처리
    def _opt10025(self, rqname, trcode):
        df_name = ''    
        data_cnt = self._get_repeat_cont(trcode, '매물대집중')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['OPT10025']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self.stockcode = add['종목코드'][0]
            df_name = self._df_generator('매물대집중', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'매물대집중 정보 {data_cnt}건 수신')          
    
    # The following methods preprocess received data from the server and generate data for strategies
    def _floatize_df(self, df_name):
        '''df_name should be one string'''
        # print('df_name,  self.tr_data[charts][df_name].columns: in _floatize_df: ', df_name, self.tr_data['charts'][df_name].columns)
        self.tr_data['charts'][df_name] = self.tr_data['charts'][df_name].astype('string')
        sort_col = ['체결시간'] if '분' in df_name else ['일자']
        self.tr_data['charts'][df_name].sort_values(sort_col, ascending=True, inplace=True)
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

    def _find_buy_sell(self):
        orders = {'buy':[], 'sell':[]}
        buy_conditions = {}
        sell_conditions = {}
        stocks = []
        # initial formatting in the first layer for dictionaries , buy_conditions and sell_conditions
        for df_name in self.tr_data['charts'].keys():
            stock = df_name.split('_')[0]
            stocks.append(stock)
            buy_conditions[stock] = {}
            sell_conditions[stock] = {}

        # initial formatting in the second layer for dictionaries , buy_conditions and sell_conditions        
        for stock in stocks:
            for condition in ['MA', 'Bollinger']:
                buy_conditions[stock][condition] = True
                sell_conditions[stock][condition] = True

        for df_name in self.tr_data['charts'].keys():
            if '월봉' in df_name or '주봉' in df_name or '일봉' in df_name or '60분' in df_name or '30분' in df_name or '10분' in df_name or '3분' in df_name:
                for idx in range(-60, 0):
                    if self.tr_data['charts'][df_name]['MA60'].values[idx] < self.tr_data['charts'][df_name]['MA20'].values[idx] < self.tr_data['charts'][df_name]['MA10'].values[idx] < self.tr_data['charts'][df_name]['MA5'].values[idx] < self.tr_data['charts'][df_name]['MA3'].values[idx]:
                        stock = self.tr_data['charts'][df_name].split('_')[0]
                        buy_conditions[stock]['MA'] = buy_conditions[stock]['MA'] and True
                        sell_conditions[stock]['MA'] = False
                    else:
                        stock = self.tr_data['charts'][df_name].split('_')[0]                        
                        buy_conditions[stock]['MA'] = False
                        sell_conditions[stock]['MA'] = sell_conditions[stock]['MA'] and True
            if '60분' in df_name or '30분' in df_name or '10분' in df_name or '5분' in df_name or '3분' in df_name or '1분' in df_name:                
                if self.tr_data['charts'][df_name]['PB'].values[-1] < 0.2 and self.tr_data['charts'][df_name]['SQZ'].values[-1] < 10:
                    stock = self.tr_data['charts'][df_name].split('_')[0]
                    buy_conditions[stock]['Bollinger'] = buy_conditions[stock]['Bollinger'] and True
                    sell_conditions[stock]['Bollinger'] = False
                elif self.tr_data['charts'][df_name]['PB'].values[-1] > 0.8:
                    stock = self.tr_data['charts'][df_name].split('_')[0]
                    buy_conditions[stock]['Bollinger'] = False
                    sell_conditions[stock]['Bollinger'] = sell_conditions[stock]['Bollinger'] and True
        
        for stock, ismet in buy_conditions.items():
            if all(ismet.values()):
                orders['buy'].append(stock)
        for stock, ismet in sell_conditions.items():
            if all(ismet.values()):
                orders['sell'].append(stock)

        return orders             

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
        for _ in range(10):
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('기준일자', date_or_tick)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data(str.upper(trcode), trcode, 2, '0002')
    
    def request_monthly_chart(self, stock, date, pricetype=1):
        self.requesting_time_unit = '월봉'
        self._chart_request(stock, date, pricetype)
       
    def request_weekly_chart(self, stock, date, pricetype=1):
        self.requesting_time_unit = '주봉'
        self._chart_request(stock, date, pricetype)
      
    def request_daily_chart(self, stock, date, pricetype=1):  
        self.requesting_time_unit = '일봉'
        self._chart_request(stock, date, pricetype)

    def request_minute_chart(self, stock, mintime=30, pricetype=1):
        self.requesting_time_unit = str(mintime)+'분'
        self._chart_request(stock, mintime, pricetype)
    
    def request_tick_chart(self, stock, ticktime=1, pricetype=1):
        self.requesting_time_unit = str(ticktime)+'틱'
        self._chart_request(stock, ticktime, pricetype)

    # def request_real_data(self, codelist, fidlist, opttype='1', scrno='0100'):            
    #     self.set_real_data(scrno, codelist, fidlist, opttype)
        
    def request_real_chart(self, *stocks):
        codelist = [self.all_stocks['stockkeys'][stock] for stock in stocks]
        fidlist = [fid for fid in self.fids_dict['주식체결'].keys()]
        self.set_real_data('0100', codelist, fidlist, 1)
      
    
    # Simplified chart request functions. Return df_name
    def min1(self, stock):
        self.request_minute_chart(stock, 1, pricetype=1)
    def min3(self, stock):
        self.request_minute_chart(stock, 3, pricetype=1)
    def min5(self, stock):
        self.request_minute_chart(stock, 5, pricetype=1)
    def min10(self, stock):
        self.request_minute_chart(stock, 10, pricetype=1)
    def min30(self, stock):
        self.request_minute_chart(stock, 30, pricetype=1)
    def min60(self, stock):
        self.request_minute_chart(stock, 60, pricetype=1)
    def daily(self, stock):
        self.request_daily_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
    def weekly(self, stock):
        self.request_weekly_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
    def monthly(self, stock):
        self.request_monthly_chart(stock, datetime.today().strftime('%Y%m%d'), pricetype=1)
    
    def onestop_stock(self, *stocks):
        chart_funcs = [self.min1, self.min3, self.min5, self.min10, self.min30, self.min60, self.daily, self.weekly, self.monthly]
        
        if type(stocks[0]) != str:
            stocks = stocks[0]       
        for stock in stocks:
            self.following_stocks.add(stock)        
        for chart_func in chart_funcs:
            for stock in stocks:
                chart_func(stock)
            print('\n')
        
        while True:           
            if len(self.tr_data['charts'].keys()) == len(chart_funcs)*len(stocks):
                break          

        self._apply_strategies(self.tr_data['charts'].keys())
        print('All data processed to apply strategies\n')                

        with sqlite3.connect('test_tr_data.db') as file:
            for df_name in self.tr_data['charts'].keys():
                self.tr_data['charts'][df_name].to_sql(df_name, file, if_exists='append')         

    
    # 가격급등락요청
    def request_sudden_price_change(self, market='000', updown='1', timeunit='1', dayormin='1', volume='01000', 
                                    stockcategory='1', creditcategory='0', pricecategory='0', includeendprice='1'):
        inputs = {'시장구분':market, '등락구분':updown, '시간구분':timeunit, '시간':dayormin, '거래량구분':volume, 
                  '종목조건':stockcategory, '신용조건':creditcategory, '가격조건':pricecategory, '상하한가포함':includeendprice}
        for trname, trcode in inputs.items():
            self.set_input_value(trname, trcode)
        self.comm_rq_data('OPT10019', 'opt10019', 0, '0050')   
    
    #거래량급증요청
    def request_sudden_volume_change(self, market='000', upcategory='2', timeunit='1', volumecategory='1000', 
                                     minute='3', stockcategory='0', pricecategory='0'):   
        inputs = {'시장구분':market, '정렬구분':upcategory, '시간구분':timeunit, '거래량구분':volumecategory, 
                  '시간':minute, '종목조건':stockcategory, '가격구분':pricecategory}
        for trname, trcode in inputs.items():
            self.set_input_value(trname, trcode)
        self.comm_rq_data('OPT10023', 'OPT10023', 0, '0051')
  
    # 매물대집중요청    
    def request_volume_profile_point_of_control(self, market='000', poc_ratio='10', includecurrentprice='1', number='5', period='50'):
        inputs = {'시장구분':market, '매물대집중':poc_ratio, '현재가진입':includecurrentprice, '매물대수':number, '주기구분':period}
        for trname, trcode in inputs.items():
            self.set_input_value(trname, trcode)
        self.comm_rq_data('OPT10025', 'OPT10025', 0, '0052')
    
    # Simplified functions for sudden chages in prices, volume, and volume profile (point of control)    
    def priceup(self, dayormin='1', volume='01000'):
        self.request_sudden_price_change('000', '1', '1', dayormin, volume) 
    def pricedown(self, dayormin='1', volume='00000'):
        self.request_sudden_price_change('000', '2', '1', dayormin, volume)          
    def volumeup(self, minute='3'):
        self.request_sudden_volume_change('000', '2', '1', '5', minute)
    def poc(self, number='5', poc_ratio='10', period='50'):
        self.request_volume_profile_point_of_control('000', poc_ratio, '1', number, period)
     
    def _find_volitility(self):
        self.priceup()
        self.volumeup()
        self.poc()

        column = {'가격급등락':['급등률'], '거래량급증':['급증률'], '매물대집중':['등락률']}
        stocks = {}
        ideal = set() 
        seen = set()
        for df_name, df in self.tr_data['volitility'].items():
            self.tr_data['volitility'][df_name][column[df_name]] = self.tr_data['volitility'][df_name][column[df_name]].astype('float')
            self.tr_data['volitility'][df_name].sort_values(column[df_name], ascending=False, inplace=True)
            stocks[df_name] = self.tr_data['volitility'][df_name]['종목명'][:15]
            for stock in stocks[df_name]:
                if stock in seen:
                    ideal.add(stock)
                else:
                    seen.add(stock)
        return ideal, stocks
    
    def onestop_volitility(self):
        stocks = self._find_volitility()
        if len(stocks[0]):
            target_stocks = stocks[0]
            print(f'\n거래량급증, 가격급등, 매물대집중 모두 충족하는 종목 {len(target_stocks)}개 발견. 해당종목 분석.\n')
        else:
            target_stocks = stocks[1]['거래량급증']            
            print(f'\n거래량급증, 가격급등, 매물대집중 모두 충족하는 종목 미발견. 거래량급증 상위{len(target_stocks)} 분석.\n')

        self.onestop_stock(target_stocks)

        with sqlite3.connect('backtest_data.db') as file:
            for df_name, df in self.tr_data['charts'].items():
                df.to_sql(df_name, file, if_exists='append')

        # self._apply_strategies()           

    def buy(self, stock, price, qty=1):
        self.make_order(stock, price, qty)
    def sell(self, stock, price, qty=1):
        self.make_order(stock, price, qty)
    def cancel(self, stock, price, qty, orderno):
        self.make_order(stock, price, qty, '00', 1, orderno) 
                        
app = QApplication(sys.argv)
kiwoom = Kiwoom()
kiwoom.onestop_volitility()
