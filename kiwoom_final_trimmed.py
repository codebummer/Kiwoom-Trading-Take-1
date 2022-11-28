from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time
import sys, os, json
from datetime import datetime
# import matplotlib.pyplot as plt

#change the current working directory
# path = r'D:\myprojects\TradingDB' + '\\' + datetime.today().strftime('%Y-%m-%d')
path = r'D:\myprojects\TradingDB'
if not os.path.exists(path):
     os.mkdir(path)
os.chdir(path) 

# TR_REQ_TIME_INTERVAL = 0.2
TR_REQ_TIME_INTERVAL = 0.4

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
        self.remaining_data = False
        self.fidlist = []
        self.tr_data = {}
        self.stockcode_non_realtime = 0        
        self.requesting_time_unit = ''
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
            # Values below this line can be rearranged in its order
            # You can even remove FID from the values if you don't need that FID
            'opt10079' : ['현재가', '거래량', '체결시간', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분',
                            '종목정보', '수정주가이벤트', '전일종가'],
            'opt10080' : ['현재가', '거래량', '체결시간', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분', '소업종구분', 
                            '종목정보', '수정주가이벤트', '전일종가'],
            'opt10081' : ['종목코드', '현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가', '수정주가구분', '수정비율', '대업종구분',
                            '소업종구분', '종목정보', '수정주가이벤트', '전일종가'],
            'OPTKWFID' : ['종목코드', '종목명', '현재가', '기준가', '전일대비', '전일대비기호', '등락율', '거래량', '거래대금', '체결량', 
                            '체결강도', '전일거래량대비', '매도호가', '매수호가', '매도1차호가', '매도2차호가', '매도3차호가', '매도4차호가',
                            '매도5차호가', '매수1차호가', '매수2차호가', '매수3차호가', '매수4차호가', '매수5차호가', '상한가', '하한가', '시가',
                            '고가', '저가', '종가', '체결시간', '예상체결가', '예상체결량', '자본금', '액면가', '시가총액', '주식수', '호가시간',
                            '일자', '우선매도잔량', '우선매수잔량', '우선매도건수', '우선매수건수', '총매도잔량', '총매수잔량', '총매도건수', 
                            '총매수건수', '패리티', '기어링', '손익분기', '자본지지', 'ELW행사가', '전환비율', 'ELW만기일', '미결제약정', '미결제전일대비',
                            '이론가', '내재변동성', '델타', '감마', '쎄타', '베가', '로']
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

    def _make_timer(self):
        self.savetimer = QTimer()
        self._time_event_handler()
        self.timeset()
    
    def _time_event_handler(self):
        self.savetimer.timeout.connect(self._timersave_df)
    
    def timeset(self, minute_interval=5):
        millisec_interval = minute_interval * 60_000
        self.savetimer.setInterval(millisec_interval)
        self.savetimer.start()
        print(f'Autosaving interval is set for {minute_interval} minute(s)')        
    
    def _timersave_df(self):
        print('\nAutosaving in progress...')
        for df_name, df in self.tr_data.items():
            names = df_name.split('_')
            table = names[0] if len(names) == 4 else names[0]+' '+names[1]
            self._data_to_sql(table, df_name+'.db', df)
            print(f'{table} is saved in {df_name}.db')            
        self.tr_data = {}        
        minute_interval = int(self.savetimer.interval()/60_000)
        print(f'\nAutosaving for every {minute_interval} minute completed.')
        
    def data_from_sql(self, tablename, filename):
        with sqlite3.connect(filename) as file:
            return pd.read_sql(f'SELECT * FROM [{tablename}]', file)    
    
    def _data_to_sql(self, tablename, filename, df):
        with sqlite3.connect(filename) as file:
            df.to_sql(tablename, file, if_exists='append')
            
    def _df_generator(self, realtype, stockcode, data):   
        if stockcode == '':
            print('\n\nrealtype, stockcode, data in df_generator: \n', realtype, stockcode, data)
            df_name = realtype+'_'+datetime.today().strftime('%Y_%m_%d')
        else:
            print('\n\nrealtype, stockcode, stock, data in df_generator: \n', realtype, stockcode, self.all_stocks['tickerkeys'][stockcode], data)
            df_name = self.all_stocks['tickerkeys'][stockcode]+'_'+realtype+self.requesting_time_unit+'_'+datetime.today().strftime('%Y_%m_%d')
            
        if df_name in self.tr_data.keys():
            self.tr_data[df_name] = self.tr_data[df_name].append(pd.DataFrame(data), ignore_index=True)
            return df_name, self.tr_data[df_name]
        else:
            self.tr_data[df_name] = pd.DataFrame(data)
            return df_name, self.tr_data[df_name]
            
    def account_info(self):
        #GetLoginInfo() takes its argument as a list form. Put all the input values in []
        self.account_num = self.dynamicCall('GetLoginInfo(QString)', ['ACCNO']).strip(';')
        print(self.account_num)

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
        
        if prenext == 2:
            self.remaining_data = True
        elif prenext == 0:
            self.remaining_data = False
            
        print('scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4: ->in _receive_tr_data\n',\
                scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4)        

        if rqname == 'OPT10081':
            df_name, df = self._opt10081(rqname, trcode)

        elif rqname == 'OPT10079':
            df_name, df = self._opt10079(rqname, trcode)

        elif rqname == 'OPT10080':
            df_name, df = self._opt10080(rqname, trcode)

        elif rqname == 'OPTKWFID':
            df_name, df = self._optkwfid(trcode)
    
    def _receive_real_data(self, code, realtype, realdata):
        if realtype == '주식시세':
            self._realtype_stock_status(code)            
        elif realtype == '주식체결':
            self._realtype_stock_made(code)            
        elif realtype == '주문체결':
            self._realtype_order_made(code)
    
    def _receive_msg(self, scrno, rqname, trcode, msg):
        print('\n\nscrno, rqname, trcode, msg: ->in _receive_msg\n', scrno, rqname, trcode, msg)
        add = {}
        stock = self.all_stocks['tickerkeys'][self.stockcode_non_realtime]
        msg_trimmed = msg.split()
        msg_trimmed[0] = msg_trimmed[0].strip('[]')
        add[datetime.now().strftime('%H:%M:%S')] = [stock, trcode, msg_trimmed[0], msg_trimmed[1], msg_trimmed[2]]
        self.tr_data['주문메세지'] = add  

    def _receive_chejan_data(self, gubun, itemcnt, fidlist): 
        '''
        itemcnt in _receive_chejan_data is the number of fid elements in fidlist
        fidlist is received in the form of a one long string connected by ;
        fidlist example : 9201;9203;9205;9001;912;913;302;900;901;902;903;904;905;906;907;908;909;910
        itemcnt for the above fidlist exmaple will be its number, 18    
        '''   
        print('gubun, type(gubun): -> in _receive_chejan_data\n', gubun, type(gubun))
        if gubun == '0': #order placed and made 
            self._real_chejan_placed_made(itemcnt, fidlist)
        elif gubun == '1':
            self._domestic_balance_change(itemcnt, fidlist)
    
    def _domestic_balance_change(self, itemcnt, fidlist): #itemcnt is the number of fid elements in fidlist
        print('\nitemcnt, fidlist: -> in _domestic_balance_chanage\n', itemcnt, fidlist)
        fidlist = fidlist.split(';')
        fidlist_checked = []
        fid_indict = [str(key) for key in self.fids_dict['신용잔고'].keys()]
        for fid in fidlist:
            if fid in fid_indict:
                fidlist_checked.append(fid)
        add = {}
        for fid in fidlist_checked:
            add[self.fids_dict['신용잔고'][int(fid)]] = [self._get_chejan_data(fid)]
        #the second argument, stockcode, is assigned '', 
        #which makes _df_generator df_name without stock name in it.
        df_name, df = self._df_generator('잔고변경', '', add) 
    
    def _realtype_stock_status(self, code):
        add= {}
        fidlist = self.fids_dict['주식시세']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주식시세', code, add)

    def _realtype_stock_made(self, code): 
        add= {}
        fidlist = self.fids_dict['주식체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주식체결', code, add)
 
    def _realtype_order_made(self, code):
        add= {}
        fidlist = self.fids_dict['주문체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]

        self.requesting_time_unit = ''
        df_name, df = self._df_generator('주문체결', code, add)   
    
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_chejan_data(self, fid):
        return self.dynamicCall('GetChejanData(int)', fid)

    def _get_repeat_cont(self, trcode, recordname):   
        print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _real_chejan_placed_made(self, itemcnt, fidlist): #itemcnt is the number of fid elements in fidlist
        print('\nitemcnt, fidlist: -> in_real_chejan_placed_made\n', itemcnt, fidlist)
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
        df_name, df = self._df_generator('체결잔고', '', add) 

    def _opt10080(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식분봉차트')
        # df_name = ''
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10080']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            df_name, df = self._df_generator('주식분봉차트', self.stockcode_non_realtime, add)
        return df_name, df      
 
    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식일봉차트')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10081']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            df_name, df = self._df_generator('주식일봉차트', self.stockcode_non_realtime, add)
        return df_name, df
 
    def _opt10079(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '주식틱차트')        
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10079']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]  
            df_name, df = self._df_generator('주식틱차트', self.stockcode_non_realtime, add)
        return df_name, df

    def _optkwfid(self, trcode):
        data_cnt = self._get_repeat_cont(trcode, '관심종목')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['OPTKWFID']:
                add[key] = [self._get_comm_data(trcode, 'OPTKWFID', idx, key)]
            df_name, df = self._df_generator('관심종목', add['종목코드'][0], add)
        return df_name, df          

    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()

    def request_daily_chart(self, stock, date, iter=100, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        stockcode = self.all_stocks['stockkeys'][stock]
        self.stockcode_non_realtime = stockcode  
        self.requesting_time_unit = ''      
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('기준일자', date)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10081', 'opt10081', 0, '0001')

        for _ in range(iter):
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('기준일자', date)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10081', 'opt10081', 2, '0002')

    def request_minute_chart(self, stock, mintime=30, iter=100, pricetype=1):
        '''
        stock: name of a stock
        mintime: one of 1, 3, 5, 10, 15, 30, 45, 60 
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        stockcode = self.all_stocks['stockkeys'][stock]
        self.stockcode_non_realtime = stockcode      
        self.requesting_time_unit = str(mintime)+'분'
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('틱범위', mintime)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10080', 'opt10080', 0, '0003')

        for _ in range(iter):
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('틱범위', mintime)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10080', 'opt10080', 2, '0004')
    
    def request_tick_chart(self, stock, ticktime=1, iter=100, pricetype=1):
        '''
        stock: name of a stock
        ticktime: one of 1, 3, 5, 10, 30
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        stockcode = self.all_stocks['stockkeys'][stock]
        self.stockcode_non_realtime = stockcode      
        self.requesting_time_unit = str(ticktime)+'틱'
        self.set_input_value('종목코드', stockcode)
        self.set_input_value('틱범위', ticktime)
        self.set_input_value('수정주가구분', pricetype)
        self.comm_rq_data('OPT10079', 'opt10079', 0, '0003')

        print('Request iteration: ', iter)
        for _ in range(iter):
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.set_input_value('종목코드', stockcode)
            self.set_input_value('틱범위', ticktime)
            self.set_input_value('수정주가구분', pricetype)
            self.comm_rq_data('OPT10079', 'opt10079', 2, '0004')
    
    def request_mass_data(self, *stocklist, prenext=0):
        code_list = ''
        stocks = [] 
        #when stocklist is a long string with stock names separated with ,
        #'삼성전자, 현대차, LG전자'
        if type(stocklist) == str:
            for stock in stocklist[0].split(','):
                stocks.append(stock.strip())
        #when one list filled with stock name strings, it will actually be a list covered with a tuple
        #request_mass_data(stocks[:100]) -> stocks[:100] is in the form of ['삼성전자', '현대차']
        #the stocklist argument gets that input in the form of (['삼성전자', '현대차'])
        elif type(stocklist[0]) == list: 
            stocks = stocklist[0]
        else: #when stocklist is a list filled with strings. stocklist=['삼성전자', '현대차']
            stocks = stocklist
        codecnt = len(stocks)
        for idx, stock in enumerate(stocks):      
            if idx == 0:
                code_list += self.all_stocks['stockkeys'][stock]
            else:
                code_list += ';'+self.all_stocks['stockkeys'][stock] #CommKwRqData() receives multiple stock tickers as one string separated with ;
        print('\n\nRequesting the real time data of the following tickers: ', code_list)
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
        self.stockcode_non_realtime = stockcode
        print('\nself.account_num, ordertype, stockcode, qty, price, hogagb, orderno:\n', self.account_num, ordertype, stockcode, qty, price, hogagb, orderno)
        self.set_order('testuser', '0006', self.account_num, ordertype, stockcode, qty, price, hogagb, orderno)
 
                        
app = QApplication(sys.argv)

kiwoom = Kiwoom()

type(kiwoom.account_num)

# if you want, set timer interval (minutes) for autosaving. Default interval is set to 5 minutes.
kiwoom.timeset(1)
# kiwoom.make_order('삼성전자', 61100, 1, '03', 2)
# kiwoom.request_tick_chart('삼성전자', 1)
tick = lambda stock, iter=100: kiwoom.request_tick_chart(stock, 1, iter)
# stocks = lambda x: [i.strip() for i in x.split(',')]
# for stock in stocks('삼성전자, 현대차, 컬러레이'):
#     tick(stock)
# tick('컬러레이')
tick('삼성전자')
# kiwoom.request_minute_chart('삼성전자', 30)
# kiwoom.request_daily_chart('삼성전자', '20221125')
# kiwoom.request_mass_data('삼성전자, NAVER, 컬러레이, 현대차, 카카오, LG에너지솔루션')
# stocks = list(kiwoom.all_stocks['stockkeys'].keys())
# kiwoom.request_mass_data(stocks[50:60])
# print(kiwoom.all_stocks)
