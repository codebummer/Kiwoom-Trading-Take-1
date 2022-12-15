from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import sqlite3
import pandas as pd
import time, asyncio
import sys, os, json, logging
from datetime import datetime
from TradingDB.kiwoompersonal import *
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
        self.get_balance()
        self.get_account_status()        
        self.all_stocks = self.stock_ticker()
        self._make_timer()  

    def OCX_available(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')

    def reset(self):
        self.account_num = 0
        self.remaining_data = True
        self.fidlist = []
        self.tr_data = {'noncharts':{}, 'volitility':{}, 'realcharts':{}, 'charts':{}}
        '''
        self.tr_data will contain all the data this code will generate. It has a complicated structure as following:
        
        self.tr_data = { 
        
        'noncharts' 비차트관련 모든 수신데이터(주문체결, 잔고수신...):      -> no need to analyze
            {df_name named realtype i.e. 주식시세: data in dataframe},
            {df_name 잔고수신: dataframe},
            {df_name 주문메세지: dataframe},
            {df_name 예수금상세현황: dataframe},
            {df_name 삼성전자_주문체결:dataframe},
            .......
        
        All charts data below should be analyzed. That's why they're categorized separately.

        'volitility' 실시간 변동성관련 모든 수신데이터('가격급등락', '거래량급증', '매물대집중'): -> need to analyze (real time)
            {df_name named stock+_+realtype i.e. 삼성전자_가격급등락: data in dataframe},
            {df_name 삼성전자_거래량급증: dataframe},
            .......

        'realcharts' 실시간 차트 관련 모든 수신데이터 (주식체결, 주식시세):                 -> need to analyze (real time)
            {df_name named stock+_+realtype i.e. 삼성전자_주식체결: data in dataframe},
            {df_name 삼성전자_주식시세:dataframe},            
        
        'charts' 비실시간 차트관련 모든 수신데이터:                                        -> need to analyze (non real time)
            {df_name named stock+_+realtype+_+self.requesting_time_unit i.e. 삼성전자_주식분봉차트_30분봉: data in dataframe },
            {df_name 삼성전자_주식일봉차트: dataframe},
            .......               
                
        }
        
        '''
        self.stockcode = 0
        self.tax_fee_ratio = 1 + (0.015+0.23+0.15)/100
        self.requesting_time_unit = ''
        self.df_names = {}
        self.starting_time, self.lapse, self.SAVING_INTERVAL = time.time(), 0, 60*10  
        self.orders = {'orders':{}, 'follow':set(), 'analyzed':0, 'limit':1_000_000, 'spent':0}
        '''
        self.orders = {'orders': {stock: {'buying': [price, number], 'bought': [price, number], 'selling': [price, number], 'sold':[price,number]},
                                  stock: {'buying': [price, number], 'bought': [price, number], 'selling': [price, number], 'sold':[price,number]},                    
                                  add keys of 'buying', 'bought', 'selling', 'sold' and their values if such values added for each stock
                                  pop keys of 'buying', 'bought', 'selling', 'sold' and their values if such values removed for each stock
                        'follow': (stock name, stock name, stock name....)
                        'analyzed' : the number of the stocks strategies are already applied to be analyzed
                                     this number helps determine if MA strategies should be evaluated again.
                                     In case len(self.orders['follow']) > self.orders['analyzed'],
                                     evaluate the stocks for MA again
                        'limit' : the amount of money set to limit daily investment
                        'spent' : the amount of money you spent to invest so far
                        
                    'orders' -> keeps all the data for the stocks you want to make orders for
                    'follow' -> keeps just stock names of the stocks you haven't yet made orders for, but want to follow
                    
                    The data structure of self.orders is designed this way to follow up all the possible changes 
                    that might happen simultaneously. In case the program scales out and you want to trade the same stock
                    sell at a price but buy at another price at the same time, 
                    self.orders should be able to keep all the status to track changes you want to make'''                         
         
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
        
        # tr list -> 주식틱차트조회요청, 주식분봉차트조회요청, 주식일봉차트, 주식주봉차트, 주식월봉차트, etc. -> non real time
        #         -> each has input and output sets  
        # FID -> id numbers of output values for 잔고, 주식체결, 주식시세, 주문체결, etc. -> real time
        #     -> output values can be identified by FID's for each real time request (잔고, 주식체결, 주식시세, 주문체결, etc.)
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
            # '잔고' : {9201:'계좌번호', 9001:'종목코드,업종코드', 302:'종목명', 10:'현재가', 930:'보유수량', 931:'매입단가', 932:'총매입단가',
            #         933:'주문가능수량', 945:'당일순매수량', 946:'매도/매수구분', 950:'당일 총 매도 손익', 951:'예수금', 27:'매도호가', 
            #         28:'매수호가', 307:'기준가', 8019:'손익율', 397:'주식옵션거래단위'},
            '잔고' : {9201:'계좌번호', 9001:'종목코드,업종코드', 917:'신용구분', 916:'대출일', 302:'종목명', 10:'현재가', 930:'보유수량', 
                        931:'매입단가', 932:'총매입가', 933:'주문가능수량', 945:'당일순매수량', 946:'매도/매수구분', 950:'당일 총 매도 손익',
                        951:'예수금', 27:'매도호가', 28:'매수호가', 307:'기준가', 8019:'손익율', 957:'신용금액', 958:'신용이자', 918:'만기일',
                        990:'당일신현손익(유가)', 991:'당일실현손익률(유가)', 992:'당일신현손익(신용)', 993:'당일실현손익률(신용)', 959:'담보대출수량'},
            
            # Values below this line, the TR list, can be rearranged in its order
            # You can even remove FID from the values if you don't need that FID
            
            # 체결정보요청
            'opt10003' : ['시간', '현재가', '전일대비', '대비율', '우선매도호가단위', '우선매수호가단위', '체결거래량', 'sign', '누적거래량', '누적거래대금', '체결강도'],
            # 주식외국인요청
            'opt10008' : ['일자', '종가', '전일대비', '거래량', '변동수량', '보유주식수', '비중', '취득가능주식수', '외국인한도', '외국인한도증감'], 
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
            # 'opw00001' : ['통화코드', '외화예수금', '원화대용평가금', '해외주식증거금', '출금가능금액(예수금)', '주문가능금액(예수금)', '외화미수(합계)', '외화현금미수금', 
            #               '연체료', 'd+1외화예수금', 'd+2외화예수금', 'd+3외화예수금', 'd+4외화예수금'],
            'opw00001' : ['예수금', '주문가능금액', 'd2+출금가능금액'],
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
            # 가격급등락요청
            'opt10019' : ['종목코드', '종목분류', '종목명', '전일대비기호', '전일대비', '등락률', '기준가', '현재가', '기준대비', '거래량', '급등률'],
            # 거래량급증요청
            'OPT10023' : ['종목코드', '종목명', '현재가', '전일대비기호', '전일대비', '등락률', '이전거래량', '현재거래량', '급증률'],
            # 매물대집중요청
            'OPT10025' : ['종목코드', '종목명', '현재가', '전일대비기호', '전일대비', '등락률', '현재거래량', '가격대시작', '가격대끝', '매물량', '매물비'],
            
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
        self.savetimer.timeout.connect(self._time_count)
    
    def timeset(self, minute_interval=3):
        millisec_interval = minute_interval * 60_000
        # millisec_interval = 0.3 * 60_000
        self.savetimer.setInterval(millisec_interval)
        self.savetimer.start()
        print(f'Auto chart data requesting interval is set for {minute_interval} minute(s)')        
        print(f'Autosaving interval is set for {minute_interval*20} minute(s)') 
    
    def _time_count(self):        
        self.timer_count += 1
        renew_list = {}
        if (self.timer_count % 3) == 0:
            renew_list['3분'] = self.min3
        if (self.timer_count % 10) == 0:
            renew_list['10분'] = self.min10          
        if (self.timer_count % 30) == 0:           
            renew_list['30분'] = self.min30
        if (self.timer_count % 60) == 0:
            renew_list['60분'] = self.min60
            self._timersave_df()
        self._timer_refresh_data(renew_list)           

    def _timer_refresh_data(self, renew_list):
        dfname_counter = len(self.tr_data['charts'].keys())
        applylist = set()

        # df_name should be input to self._apply_strategies as a list form.
        # self.min3() returns df_name as a string, 'return stock+realtype+self.requesting_time_unit',
        # which means df_name here below have to be in a list form.
        # However, this is done by the last line of this method.
        # self._apply_strategies(self.tr_data['charts'].keys()) 
        breakcount = 0           
        for renew, call in renew_list.items():
            for df_name in self.tr_data['charts'].keys():
                # if renew in df_name and stock in df_name:
                if renew in df_name:
                    breakcount += 1
                    applylist.add(df_name)
                    stock = df_name.split('_')[0]
                    self.tr_data['charts'].pop(df_name)
                    call(stock)
                    # Due to multiple stocks, it cannot break just for the first match                    
                    if breakcount == len(self.orders['follow']):
                        breakcount = 0
                        break
        
        # PyQt's signal-slot can be completed nonsequentially. 
        # When the requested data is not received, 
        # the execution of the code can be already past the requesting data procedures without waiting,
        # resulting in the code trying to index the data not yet received.
        # This will cause an error hard to fix. 
        # This is why the follwing loop is added to wait for all the data to be received 
        # before applying strategies to the data.
        # When all the data are received, the number of received data will be same as before again.
        while True:
            if dfname_counter == len(self.tr_data['charts'].keys()):
                break
      
        if len(applylist):
            print('Data updated at the set time interval')
            # multiple timers can be activated simulanteously, 
            # which is why _apply_strategies is at the bottom line of this method
            # to reflect all the possible changes at once.       
            
            # self._apply_strategies(applylist)
            self._apply_fast_strategies(applylist)
            print('Renewed data processing completed\n')

            with sqlite3.connect('test_tr_data.db') as file:
                for df_name in applylist:
                    self.tr_data['charts'][df_name].to_sql(df_name, file, if_exists='append')            
            
            self._event_loop_exit('tr')

    def _timersave_df(self):
        print('\nAutosaving in progress...')
        Skip = False
        for df_name, df in self.tr_data['noncharts'].items():       
            # The following statement makes db file names in _data_to_sql, which is different from df_name
            # df_name is same as tr_data['charts] or tr_data['noncharts'] keys, which is done in _df_generator
            for column in df.columns:
                if '일자' in column:
                    self._data_to_sql(df_name, df_name+'.db', df)
                    Skip = True
                    break
            if Skip:
                Skip = False
                continue
            else:
                self._data_to_sql(df_name+'_'+datetime.today().strftime('%Y년%m월%d일'), df_name+'.db', df)
                Skip = False
            print(f'{df_name} is saved in {df_name}.db')            
        self.tr_data['noncharts'] = {}        

        # Skip = False
        # for df_name, df in self.tr_data['realcharts'].items():       
        #     # The following statement makes db file names in _data_to_sql, which is different from df_name
        #     # df_name is same as tr_data['charts] or tr_data['noncharts'] keys, which is done in _df_generator
        #     for column in df.columns:
        #         if '일자' in column or '시간' in column:
        #             filename = df_name.split('_')[1]+'.db'
        #             self._data_to_sql(df_name, filename, df)
        #             print(f'{df_name} is saved in {filename}')            
        #             Skip = True
        #             break
        #     if Skip:
        #         Skip = False
        #         continue    
        #     else:
        #         self._data_to_sql(df_name+'_'+datetime.today().strftime('%Y년%m월%d일'), df_name+'.db', df)
        #         print(f'{df_name} is saved in {df_name}.db')       
        #         Skip = False     
        # self.tr_data['realcharts'] = {}    
            
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
        _df_generator categories transaction data into 4 categories.
        Multiple categories make it easy to process same tasks for data with similar charateristics
        i.e. self.tr_data['charts'].keys() will generate all the df_names for charts to analyze.
        This will remove necessity to put if-conditions to screen which df_name and its dataframe
        to calculate Bollinger data and MA data, etc within the same category.
        self.tr_data = {
            'noncharts'     : {dataframe},  -> 잔고변경, 체결잔고, 주문체결 Data to save. Nonreal time. Mainly orders and balance related
            'volitility'    : {dataframe},  -> 가격급등락, 거래량급증, 매물대집중 -> Mostly real time. 
            'realcharts'    : {datafrmae},  -> 주식체결, 주식시세 -> real time data the server passes once you made a request for chart data below.
            'charts'        : {dataframe}   -> 주식틱차트, 분봉차트, 일봉차트, 주봉차트, 월봉차트 -> data to analyize for strategies
        }
        '''        
        # (stock name +) realtype (+ a time unit) = df_name = tr_data['charts'] or tr['noncharts'] keys
        # 체결잔고, 잔고변경, 주문메세지 will each have one same filename with multiple table names for additional data to save
        # They also have df_name in the form of : realtype
        
        # 주식시세, 주식체결, 주문체결, 주식일봉차트, 주식틱차트, 관심종목 will have df_name consising of
        # stock_realtype_timeunit : i.e. 삼성전자_주식일봉차트_30분봉
        # When request the account balance without requesting any stock data,
        # self.stockcode stays 0 and will cause an error, trying to index self.all_stocks with it.
        if self.stockcode:
            stock = self.all_stocks['tickerkeys'][self.stockcode]
        else:
            stock = None

        if realtype in ['주식분봉차트', '주식틱차트']:    
            # df_name is same as tr_datakeys, which is done in _df_generator
            # db file names are differently named in _data_to_sql, which is done in _timersave_df  
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
        
        # 주문체결 is real time but not chart data, 
        # which falls under this category for convenience to analyze the other data at once.
        # The others are mostly non real time and non chart data.
        # 잔고변경, 체결잔고 are most typical data for this category
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
        '''
        SetRealReg(
          BSTR strScreenNo,   // 화면번호
          BSTR strCodeList,   // 종목코드 리스트
          BSTR strFidList,  // 실시간 FID리스트
          BSTR strOptType   // 실시간 등록 타입, 0또는 1
          )
          
          종목코드와 FID 리스트를 이용해서 실시간 시세를 등록하는 함수입니다.
          한번에 등록가능한 종목과 FID갯수는 100종목, 100개 입니다.
          실시간 등록타입을 0으로 설정하면 등록한 종목들은 실시간 해지되고 등록한 종목만 실시간 시세가 등록됩니다.
          실시간 등록타입을 1로 설정하면 먼저 등록한 종목들과 함께 실시간 시세가 등록됩니다
          
          ------------------------------------------------------------------------------------------------------------------------------------
          
          [실시간 시세등록 예시]
          OpenAPI.SetRealReg(_T("0150"), _T("039490"), _T("9001;302;10;11;25;12;13"), "0");  // 039490종목만 실시간 등록
          OpenAPI.SetRealReg(_T("0150"), _T("000660"), _T("9001;302;10;11;25;12;13"), "1");  // 000660 종목을 실시간 추가등록
          
          -------------------------------------------------------------------------------------------------------------------------
        '''
            
        for idx, code in enumerate(codelist):
            stock = self.all_stocks['stockkeys'][code]
            print(f'requesting data of {stock}')
            self.dynamicCall('SetRealReg(QString, QString, QString, QString)', f'00{idx+100}', code, fidlist, opttype)
                
        self._event_loop_exec('real')
        
    def set_order(self, rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno):
        #SendOrder() takes its argument as a list form. Put all the input values in []
        self.dynamicCall('SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', [rqname, scrno, accno, ordertype, code, qty, price, hogagb, orgorderno])
        stock = self.all_stocks['tickerkeys'][code]
        self._follow_stocks(stock) 
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
            
        
        # 가격급등락요청
        elif rqname == 'OPT10019':
            self._opt10019(rqname, trcode)
        #거래량급증요청
        elif rqname == 'OPT10023':
            self._opt10023(rqname, trcode)
        #매물대집중요청
        elif rqname == 'OPT10025':
            self._opt10025(rqname, trcode)

        # 예수금상세현황요청
        elif rqname == 'OPW00001':
            self._opw00001(rqname, trcode)  
        # 계좌평가현황요청
        elif rqname == 'OPW00004':
            self._opw00004(rqname, trcode)     
        # 계좌평가잔고내역요청
        elif rqname == 'OPW00018':
            self._opw00018(rqname, trcode)
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
        # When request the account balance without requesting any stock data,
        # self.stockcode stays 0 and will cause an error, trying to index self.all_stocks with it.
        if self.stockcode:
            stock = self.all_stocks['tickerkeys'][self.stockcode]
        else:
            stock = None
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
        # 구분 0: 접수 및 체결
        if gubun == '0': #order placed and made 
            self._real_chejan_placed_made(itemcnt, fidlist)
        # 구분 1: 국내주식 잔고변경
        elif gubun == '1':
            self._domestic_balance_change(itemcnt, fidlist)
        
        try:
            self._event_loop_exit('order')
        except AttributeError:
            pass

    # 접수 및 체결 수신내용처리
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
        self._df_generator('체결잔고', add)
        self._follow_stocks(add['종목명'][0])
        print(f'주문체결/체결잔고 내용수신')
            
    # update self.orders based on 계좌평가현황
    def _follow_stocks(self, stock, status=''):
        '''
        To change values in self.orders - global variable for all stocks you analyze, or order
        self.orders['orders'] keeps track of orders currently in progress or made in this session.
        This doesn't include the orders from previous sessions or in the past execution of the trading program.
        
        self.orders['follow'] keeps track of all the stocks you make or plan to make orders for '''
        # No orders bought or sold but follow stocks to analyze
        if status == 'follow':
            self.orders['follow'].add(stock)
        
        # Stocks are bought or sold and keeps following those stocks for later transactions
        elif status == '':
            self.orders['follow'].add(stock)

            # update self.orders based on 계좌평가현황
            def _check_heldstock(stock):
                df = self.tr_data['noncharts']['계좌평가현황']
                return int(df.loc[df['종목명']==stock]['보유수량'])

            record = self.tr_data['noncharts']['체결잔고'].loc[self.tr_data['noncharts']['체결잔고']['종목명']==stock].iloc[-1]
            for column in ['주문수량', '주문가격', '미체결수량', '체결가', '체결량']:
                record[column] = int(record[column])

            if stock in self.orders['orders'].keys():
                if record['미체결수량']:
                    if '매수' in record['주문구분']:
                        self.orders['orders'][stock]['buying'] = [record['주문가격'], record['주문수량']]
                    elif '매도' in record['주문구분']:
                        self.orders['orders'][stock]['selling'] = [record['주문가격'], record['주문수량']]
                elif record['체결량']:
                    if '매수' in record['주문구분']:
                        self.orders['orders'][stock]['bought'] = [record['체결가'], record['체결량']]                        
                        self.orders['orders'][stock].pop('buying')
                        self.orders['spent'] += record['체결가'] * record['체결량']
                    elif '매도' in record['주문구분']:  
                        # 계좌평가현황의 보유수량확인
                        if _check_heldstock(stock) > 0:                      
                            self.orders['orders'][stock]['sold'] = [record['체결가'], record['체결량']]
                            self.orders['orders'][stock].pop('selling')
                            self.orders['orders'][stock].pop('bought')
            else:
                if '매수' in record['주문구분']:
                    self.orders['orders'][stock] = {'buying': [record['주문가격'], record['주문수량']]}
                    self.orders['spent'] += record['체결가'] * record['체결량']
                elif '매도' in record['주문구분']:
                    if _check_heldstock(stock):                  
                        self.orders['orders'][stock] = {'selling': [record['주문가격'], record['주문수량']]}
                    else:
                        print('매수신청종목을 보유하지 않은 상황입니다. 매수신청이 불가능합니다.')             

    # 국내주식 잔고변경 수신내용처리
    def _domestic_balance_change(self, itemcnt, fidlist): #itemcnt is the number of fid elements in fidlist
        # print('\nitemcnt, fidlist: -> in _domestic_balance_chanage\n', itemcnt, fidlist)
        print('change in balance happened')
        fidlist = fidlist.split(';')
        fidlist_checked = []
        fid_indict = [str(key) for key in self.fids_dict['잔고'].keys()]
        for fid in fidlist:
            if fid in fid_indict:
                fidlist_checked.append(fid)
        add = {}
        for fid in fidlist_checked:
            add[self.fids_dict['잔고'][int(fid)]] = [self._get_chejan_data(fid)]
        df_name = self._df_generator('잔고변경', add) 
        print(f'신용잔고/잔고변경 내용수신')
    
    # 실시간 주식시세요청 결과처리
    def _realtype_stock_status(self, code):
        add= {}
        fidlist = self.fids_dict['주식시세']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.stockcode = code
        df_name = self._df_generator('주식시세', add)
        print(f'실시간 주식시세 내용수신')        

    # 실시간 주식체결 결과처리 (시장전체체결현황, NOT 내 주문체결결과)
    def _realtype_stock_made(self, code): 
        add= {}
        fidlist = self.fids_dict['주식체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]
        
        self.stockcode = code       
        stock = self.all_stocks['tickerkeys'][code]
        # Do not print 주식체결 결과처리. This has too much data to print. Save them at a set time interval at a db file instead.
        self._df_generator('주식체결', add)
 

    # 실시간 주문체결 결과처리 (내 주문체결결과)
    def _realtype_order_made(self, code):
        add= {}
        fidlist = self.fids_dict['주문체결']

        for fid, fidname in fidlist.items():
            add[fidname] = [self._get_comm_real_data(code, fid)]

        self.stockcode = code       
        stock = self.all_stocks['tickerkeys'][code]
        df_name = self._df_generator('주문체결', add)   
        print(f'실시간 주문체결 내용수신 (내 주문내역)')        

            
    def _get_comm_real_data(self, code, fid):
        return self.dynamicCall('GetCommRealData(QString, int)', code, fid)        

    def _get_chejan_data(self, fid):
        return self.dynamicCall('GetChejanData(int)', fid)

    def _get_repeat_cont(self, trcode, recordname):   
        # print('\nGetRepeatCnt: ', self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname))    
        return self.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
    
    def _get_comm_data(self, trcode, rqname, idx, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, idx, itemname).strip()
    
    # Evaluate if money is enough to make a new order
    def _is_balance_enough(self, price, qty=1):
        return self.tr_data['noncharts']['예수금상세현황']['주문가능금액'] >= price*qty*self.tax_fee_ratio
    
    # Evaluate if there exist enough stocks to sell
    def _is_stock_enough(self, stock):
        record = self.tr_data['noncharts']['계좌평가현황'].loc[self.tr_data['noncharts']['계좌평가현황']['종목명']==stock]
        return record['보유수량'].values[0]

    # 예수금상세현황요청
    def get_balance(self):
        inputs = {'계좌번호':self.account_num, '비밀번호':password, '비밀번호입력매체구분':'00', '조회구분':'2'}
        for tr_name, tr_value in inputs.items():
            self.set_input_value(tr_name, tr_value)
        self.comm_rq_data('OPW00001', 'opw00001', '0', '0200')    
    
    # 계좌평가현황요청
    def get_account_status(self):
        inputs = {'계좌번호':self.account_num, '비밀번호':password, '상장폐지조회구분':'0', '비밀번호입력매체구분':'00'}
        for tr_name, tr_value in inputs.items():
            self.set_input_value(tr_name, tr_value)
        self.comm_rq_data('OPW00004', 'OPW00004', '0', '0201')        

    
    # _opt10079 ~ _opt10081 have an item for stock codes in output values in the guidebook, 
    # but actually return blank instead of stock codes 
    
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
        # print(self.tr_data['charts'][df_name])
        
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
        # print(self.tr_data['charts'][df_name])
    
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
    
    # _optkfid is actually for simultaneous multiple stock data requests, not 관심종목
    # This actually returns stock codes in its output values
    def _optkwfid(self, rqname, trcode):
        df_name = ''    
        data_cnt = self._get_repeat_cont(trcode, '관심종목')
        add= {}
        for idx in range(data_cnt):
            for key in self.fids_dict['OPTKWFID']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self.stockcode = add['종목코드'][0]
            df_name = self._df_generator('관심종목', add)
        stock = self.all_stocks['tickerkeys'][self.stockcode]
        print(f'{stock} 관심종목 정보 {data_cnt}건 수신')  
    
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

    # 예수금상세현황
    def _opw00001(self, rqname, trcode):
        add = {}
        for key in self.fids_dict['opw00001']:
            add[key] = [self._get_comm_data(trcode, rqname, 0, key).lstrip('0')]
        df_name = self._df_generator('예수금상세현황', add)   
        if self.tr_data['noncharts'][df_name]['예수금'][0]:
            balance = int(self.tr_data['noncharts'][df_name]['예수금'][0])
        else:
            balance = 0
        if self.tr_data['noncharts'][df_name]['주문가능금액'][0]:
            cash_available = int(self.tr_data['noncharts'][df_name]['주문가능금액'][0])
        else:
            cash_available = 0        
        print(f'예수금상세현황/주문가능금액 정보수신: 예수금 {balance:,}원 / 주문가능금액 {cash_available:,}원')       

    # 계좌평가현황요쳥 결과처리
    def _opw00004(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '계좌평가현황')        
        add = {}
        for key in self.fids_dict['OPW00004']:
            add[key] = [self._get_comm_data(trcode, rqname, 0, key)]  
        df_name = self._df_generator('계좌평가현황', add)
        columns = ['종목명', '보유수량', '평균단가', '매입금액', '결제잔고']
        df = self.tr_data['noncharts'][df_name][columns]
        df.replace('', 0, inplace=True)
        for column in df.columns:
            if column not in ['종목명']:
                df[column] = df[column].astype('int')
        print('계좌평가현황정보수신\n', df)
    
    # 계좌평가잔고내역요청 결과처리
    def _opw00018(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '계좌평가잔고내역')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw00018']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('계좌평가잔고내역', add)
        print(f'계좌평가잔고내역 수신\n', self.tr_data['noncharts']['계좌평가잔고내역'])       
   
    # 계좌수익율요청 결과처리
    def _opt10085(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '계좌수익율')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opt10085']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('계좌수익율', add)
        print(f'계좌수익율 수신\n', self.tr_data['noncharts']['계좌수익율'])        

    # 당일실현손익상세요청 결과처리
    def _opt10077(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '당일실현손익상세')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw10077']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('당일실현손익상세', add)
        print(f'당일실현손익상세 수신\n', self.tr_data['noncharts']['당일실현손익상세'])      

    # 체결요청 결과처리
    def _opt10076(self, rqname, trcode):
        data_cnt = self._get_repeat_cont(trcode, '체결')
        add = {}
        for idx in range(data_cnt):
            for key in self.fids_dict['opw10076']:
                add[key] = [self._get_comm_data(trcode, rqname, idx, key)]
            self._df_generator('체결', add)
        print(f'체결 수신\n', self.tr_data['charts']['체결'])      

    # 미체결요청 결과처리
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
        buy_conditions = {}
        sell_conditions = {}
        
        for stock in self.orders['follow']:
            buy_conditions[stock] = {}
            sell_conditions[stock] = {}
            for condition in ['MA', 'Bollinger']:
                buy_conditions[stock][condition] = True
                sell_conditions[stock][condition] = True
        
        # Change MA conditions to sell
        def _mas(df_name):
            for idx in range(-60, 0):
                if self.tr_data['charts'][df_name]['MA60'].values[idx] < self.tr_data['charts'][df_name]['MA20'].values[idx] < self.tr_data['charts'][df_name]['MA10'].values[idx] < self.tr_data['charts'][df_name]['MA5'].values[idx] < self.tr_data['charts'][df_name]['MA3'].values[idx]:
                    stock = self.tr_data['charts'][df_name].split('_')[0]
                    # MA conditions should be met during the entire period of comparison,
                    # which means MA = MA and True, not MA = True
                    buy_conditions[stock]['MA'] = buy_conditions[stock]['MA'] and True
                    # MA does not change sell conditions, because selling timing will be decided only by Bollinger,
                    # so the next line is commented out
                    # sell_conditions[stock]['MA'] = False
                else:
                    stock = self.tr_data['charts'][df_name].split('_')[0]                        
                    buy_conditions[stock]['MA'] = False
                    # sell_conditions[stock]['MA'] = sell_conditions[stock]['MA'] and True
        
        def _bollinger(df_name):
            if self.tr_data['charts'][df_name]['PB'].values[-1] < 0.2 and self.tr_data['charts'][df_name]['SQZ'].values[-1] < 10:
                stock = self.tr_data['charts'][df_name].split('_')[0]
                # Bollinger will look at the number at the latest value,
                # which means Bollinger = True, not Bollinger = Bollinger and True
                buy_conditions[stock]['Bollinger'] = True
                sell_conditions[stock]['Bollinger'] = False
            elif self.tr_data['charts'][df_name]['PB'].values[-1] > 0.8:
                stock = self.tr_data['charts'][df_name].split('_')[0]
                buy_conditions[stock]['Bollinger'] = False
                sell_conditions[stock]['Bollinger'] = True

        for df_name in self.tr_data['charts'].keys():
            # MA condition is evaluated only once.
            # The following statement tells if MA condition is already evaluated    
            if self.orders['analyzed'] < len(self.orders['follow']):    
                if '월봉' in df_name or '주봉' in df_name or '일봉' in df_name:
                    _mas(df_name)

            if '분봉' in df_name:                
                _bollinger(df_name)

        # update self.orders['analyzed'] to the number of stocks analyzed for strategies
        self.orders['analyzed'] = len(self.orders['follow'])
        
        # ismet -> {condition: True or False}
        for stock, ismet in buy_conditions.items():
            # ismet.values() returns all True or False evaluations
            if all(ismet.values()):
                if stock in self.orders['orders'].keys():
                    # put 'qued' in 'buying' so that it can be identified as a stock to buy
                    self.orders[stock]['buying'] = 'qued'
                else:
                    self.orders[stock] = {'buying':'qued'}
        for stock, ismet in sell_conditions.items():
            if all(ismet.values()):
                if stock in self.orders.keys():
                    self.orders[stock]['selling'] = 'qued'
                    self.orders[stock] = {'selling':'qued'}

    def _find_fast_buy_sell(self):
        buy_conditions = {}
        sell_conditions = {}  
        
        for stock in self.orders['follow']:
            buy_conditions[stock] = {}
            sell_conditions[stock] = {}
            for condition in ['MA', 'Bollinger']:
                buy_conditions[stock][condition] = True
                sell_conditions[stock][condition] = True
        
        def _mas(df_name):
            for idx in range(-60, 0):
                if self.tr_data['charts'][df_name]['MA60'].values[idx] < self.tr_data['charts'][df_name]['MA20'].values[idx] < self.tr_data['charts'][df_name]['MA10'].values[idx] < self.tr_data['charts'][df_name]['MA5'].values[idx] < self.tr_data['charts'][df_name]['MA3'].values[idx]:
                    stock = self.tr_data['charts'][df_name].split('_')[0]
                    buy_conditions[stock]['MA'] = buy_conditions[stock]['MA'] and True
                    # MA does not change sell conditions, because selling timing will be decided only by Bollinger
                    # sell_conditions[stock]['MA'] = False
                else:
                    stock = self.tr_data['charts'][df_name].split('_')[0]                        
                    buy_conditions[stock]['MA'] = False
                    # sell_conditions[stock]['MA'] = sell_conditions[stock]['MA'] and True
        
        def _bollinger(df_name):
            if self.tr_data['charts'][df_name]['PB'].values[-1] < 0.2 and self.tr_data['charts'][df_name]['SQZ'].values[-1] < 10:
                stock = self.tr_data['charts'][df_name].split('_')[0]
                buy_conditions[stock]['Bollinger'] = True
                sell_conditions[stock]['Bollinger'] = False
            elif self.tr_data['charts'][df_name]['PB'].values[-1] > 0.8:
                stock = self.tr_data['charts'][df_name].split('_')[0]
                buy_conditions[stock]['Bollinger'] = False
                sell_conditions[stock]['Bollinger'] = True            

        for df_name in self.tr_data['charts'].keys():
            # MA condition is evaluated only once for 일봉차트.
            # The following statement tells if MA condition is already evaluated            
            if self.orders['analyzed'] < len(self.orders['follow']):    
                if '일봉' in df_name:
                    _mas(df_name)

            if '일봉' in df_name or '60분' in df_name or '3분' in df_name:     
                _bollinger(df_name)          

        # update self.orders['analyzed'] to the number of stocks analyzed for strategies    
        self.orders['analyzed'] = len(self.orders['follow'])

        # ismet -> {condition: True or False}
        for stock, ismet in buy_conditions.items():
            # ismet.values() returns all True or False evaluations
            if all(ismet.values()):
                if stock in self.orders['orders'].keys():
                    # put 'qued' in 'buying' so that it can be identified as a stock to place a buy order for
                    if 'buying' not in self.orders['orders'][stock].keys():
                        self.orders['orders'][stock]['buying'] = 'qued'
                        print(f'{stock} 매수종목으로 선정')
                    # when 'buying' is already in progress and not yet bought, let the status intact
                    else:                        
                        pass
                else:
                    self.orders[stock] = {'buying':'qued'}
        for stock, ismet in sell_conditions.items():
            # ismet.values() returns all True or False evaluations
            if all(ismet.values()):
                if stock in self.orders['orders'].keys():
                    # put 'qued' in 'selling' so that it can be identified as a stock to place a sell order for
                    if 'selling' not in self.orders['orders'][stock].keys():
                        self.orders['orders'][stock]['selling'] = 'qued'
                        print(f'{stock} 매도종목으로 선정')
                    # when 'selling' is already in progress and not yet sold, let the status intact
                    else:
                        pass
                else:
                    self.orders[stock] = {'selling':'qued'}

    def _order_strategies(self, qty=1):  
        '''number represents the number of the stocks for the orders you want to make'''
        for stock, details in self.orders['orders'].items():
            for status, values in details.items():
                if status == 'buying' and values == 'qued':
                    price = int(self.tr_data['charts'][stock+'_주식분봉차트_3분']['현재가'].values[-1])
                    if self._is_balance_enough(price, qty):
                        if self.orders['limit'] > self.orders['spent']:
                            print(f'{stock} {qty}주 {price}원에 매수주문시도')
                            self.buy(stock, price)
                        else:
                            limit = self.orders['limit']
                            spent = self.orders['spent']
                            print(f'투자한도설정액 {limit:,}원 초과. 현재투자액 {spent:,}원')
                    else:
                        print('Not enough money to make orders') 
                        break
                    # do not 'break' after queing 'buy' (evaluating for 'buying qued') 
                    # unless money is not enough to make orders
                    # because the same stock can be qued for 'selling qued'              
                if status == 'selling' and values == 'qued':
                    if self._is_stock_enough(stock):
                        price = int(self.tr_data['charts'][stock+'_주식분봉차트_3분']['현재가'].values[-1])
                        print(f'{stock} {qty}주 {price}원에 매도주문시도')
                        self.sell(stock, price, qty)
                    else:
                        print(f'{stock} 보유주식없음. 매수불가.')    
    
    def _auto_orders(self, qty=1):
        '''
        qty: the number of the stocks for the orders you want to make.
        executes the following methods.
        self._apply_strategies(): generates dataframes with necessary data for strategies
        self._find_buy_sell(): find stocks to buy and sell
        self._order_strategies(): place actual orders as long as money is enough
        '''
        df_names = [df_name for df_name in self.tr_data['charts'].keys()]
        self._apply_strategies(df_names)
        self._find_buy_sell()
        self._order_strategies(qty)
    
    def _auto_fast_orders(self, qty=1):
        '''
        qty: the number of the stocks for the orders you want to make.
        executes the following methods.
        self._apply_fast_strategies()
        self._find_fast_buy_sell()
        self._order_strategies()
        '''        
        df_names = [df_name for df_name in self.tr_data['charts'].keys()]
        self._apply_fast_strategies(df_names)
        self._find_fast_buy_sell()
        self._order_strategies(qty)                     
      
    # *inputs take multiple functions to use and a list form of input values in order.
    # The functions will be inputs[:-1] and input values will be imputs[-1]
    def _apply_strategies(self, df_names):
        '''input df_names not stock names. df_names should be in a list form'''
        def _fmap(*inputs):
            '''*inputs should be functions first and values last. And the values should be in a list form'''
            for func in inputs[:-1]:
                for input in inputs[-1]:
                    func(input)
        _fmap(self._floatize_df, self._mas, self._bollinger, self._RSI, self._MFI, self._stochastic, df_names)  
        print('All data processed to apply strategies\n') 
    
    def _apply_fast_strategies(self, df_names):
        '''input df_names not stock names. df_names should be in a list form'''
        def _fmap(*inputs):
            '''*inputs should be functions first and values last. And the values should be in a list form'''
            for func in inputs[:-1]:
                for input in inputs[-1]:
                    func(input)                    
        for df_name in df_names:
            if '일봉' in df_name:
                _fmap(self._floatize_df, self._mas, self._bollinger, self._RSI, self._MFI, self._stochastic, [df_name])
            elif '일봉' in df_name or '60분' in df_name or '3분' in df_name:
                _fmap(self._floatize_df, self._bollinger, self._RSI, self._MFI, self._stochastic, [df_name])        
        print('All data processed to apply strategies\n') 

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
    
    def request_monthly_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '월봉'
        self._follow_stocks(stock, 'follow')        
        self._chart_request(stock, date, pricetype)
       
    def request_weekly_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '주봉'
        self._follow_stocks(stock, 'follow')   
        self._chart_request(stock, date, pricetype)
      
    def request_daily_chart(self, stock, date, pricetype=1):
        '''
        stock: 주식종목명
        date: 일자 YYYYMMDD
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''
        self.requesting_time_unit = '일봉'
        self._follow_stocks(stock, 'follow')   
        self._chart_request(stock, date, pricetype)

    def request_minute_chart(self, stock, mintime=30, pricetype=1):
        '''
        stock: name of a stock
        mintime: one of 1, 3, 5, 10, 15, 30, 45, 60 
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''   
        self.requesting_time_unit = str(mintime)+'분'
        self._follow_stocks(stock, 'follow')   
        self._chart_request(stock, mintime, pricetype)
    
    def request_tick_chart(self, stock, ticktime=1, pricetype=1):
        '''
        stock: name of a stock
        ticktime: one of 1, 3, 5, 10, 30
        iter: 데이터 수신 반복회수 (1회 수신 900여개)
        pricetype: 1.유상증자 2.무상증자 4.배당락 8.액면분할 16.액면병합 32.기업합병 64.감자 256.권리락
        '''  
        self.requesting_time_unit = str(ticktime)+'틱'
        self._follow_stocks(stock, 'follow')   
        self._chart_request(stock, ticktime, pricetype)

    # def request_real_data(self, codelist, fidlist, opttype='1', scrno='0100'):            
    #     self.set_real_data(scrno, codelist, fidlist, opttype)
        
    def request_real_chart(self, *stocks):
        for stock in stocks:
            self._follow_stocks(stock, 'follow')
        codelist = [self.all_stocks['stockkeys'][stock] for stock in stocks]
        fidlist = [fid for fid in self.fids_dict['주식체결'].keys()]
        self.set_real_data('0100', codelist, fidlist, 1)

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
        
        for stock in stocks:
            self._follow_stocks(stock, 'follow')
 
        codecnt = len(stocks)
        for idx, stock in enumerate(stocks):      
            if idx == 0:
                code_list += self.all_stocks['stockkeys'][stock]
            else:
                code_list += ';'+self.all_stocks['stockkeys'][stock] #CommKwRqData() receives multiple stock tickers as one string separated with ;
        # print('\n\nRequesting the real time data of the following tickers: ', code_list)
        self.comm_kw_rq_data(code_list, prenext, codecnt, typeflag=0, rqname='OPTKWFID', scrno='0005')      
    
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

    # 가격급등락요청
    def request_sudden_price_change(self, market='000', updown='1', timeunit='1', dayormin='1', volume='01000', 
                                    stockcategory='1', creditcategory='0', pricecategory='0', includeendprice='1'):
        '''	
        시장구분 = 000:전체, 001:코스피, 101:코스닥, 201:코스피200
        등락구분 = 1:급등, 2:급락
        시간구분 = 1:분전, 2:일전
        시간 = 분 혹은 일입력
        거래량구분 = 00000:전체조회, 00010:만주이상, 00050:5만주이상, 00100:10만주이상, 00150:15만주이상, 00200:20만주이상, 00300:30만주이상, 00500:50만주이상, 01000:백만주이상
        종목조건 = 0:전체조회,1:관리종목제외, 3:우선주제외, 5:증100제외, 6:증100만보기, 7:증40만보기, 8:증30만보기
        가격조건 = 0:전체조회, 1:1천원미만, 2:1천원~2천원, 3:2천원~3천원, 4:5천원~1만원, 5:1만원이상, 8:1천원이상
        상하한포함 = 0:미포함, 1:포함
        '''
        inputs = {'시장구분':market, '등락구분':updown, '시간구분':timeunit, '시간':dayormin, '거래량구분':volume, 
                  '종목조건':stockcategory, '신용조건':creditcategory, '가격조건':pricecategory, '상하한가포함':includeendprice}
        for trname, trcode in inputs.items():
            self.set_input_value(trname, trcode)
        self.comm_rq_data('OPT10019', 'opt10019', 0, '0050')   
    
    #거래량급증요청
    def request_sudden_volume_change(self, market='000', upcategory='2', timeunit='1', volumecategory='1000', 
                                     minute='3', stockcategory='0', pricecategory='0'):
        '''
       	시장구분 = 000:전체, 001:코스피, 101:코스닥
        정렬구분 = 1:급증량, 2:급증률
        시간구분 = 1:분, 2:전일
        거래량구분 = 5:5천주이상, 10:만주이상, 50:5만주이상, 100:10만주이상, 200:20만주이상, 300:30만주이상, 500:50만주이상, 1000:백만주이상
        시간 = 분 입력
        종목조건 = 0:전체조회, 1:관리종목제외, 5:증100제외, 6:증100만보기, 7:증40만보기, 8:증30만보기, 9:증20만보기
        가격구분 = 0:전체조회, 2:5만원이상, 5:1만원이상, 6:5천원이상, 8:1천원이상, 9:10만원이상
        '''
        inputs = {'시장구분':market, '정렬구분':upcategory, '시간구분':timeunit, '거래량구분':volumecategory, 
                  '시간':minute, '종목조건':stockcategory, '가격구분':pricecategory}
        for trname, trcode in inputs.items():
            self.set_input_value(trname, trcode)
        self.comm_rq_data('OPT10023', 'OPT10023', 0, '0051')
  
    # 매물대집중요청    
    def request_volume_profile_point_of_control(self, market='000', poc_ratio='10', includecurrentprice='1', number='5', period='50'):
        '''
        시장구분 = 000:전체, 001:코스피, 101:코스닥
        매물집중비율 = 0~100 입력
        현재가진입 = 0:현재가 매물대 집입 포함안함, 1:현재가 매물대 집입포함
        매물대수 = 숫자입력
        주기구분 = 50:50일, 100:100일, 150:150일, 200:200일, 250:250일, 300:300일
        '''
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
    
    def buy(self, stock, price, qty=1):
        self.make_order(stock, price, qty, '00', '1')
    def sell(self, stock, price, qty=1):
        self.make_order(stock, price, qty, '00', '2')
    def cancelbuy(self, stock, price, qty, orderno):
        self.make_order(stock, price, qty, '00', '3', orderno) 
    def cancelsell(self, stock, price, qty, orderno):
        self.make_order(stock, price, qty, '00', '4', orderno) 
    def changebuy(self, stock, price, qty, orderno):
        self.make_order(stock, price, qty, '00', '5', orderno) 
    def changesell(self, stock, price, qty, orderno):
        self.make_order(stock, price, qty, '00', '6', orderno) 

    def onestop_stock(self, *stocks, qty=1):
        chart_funcs = [self.min1, self.min3, self.min5, self.min10, self.min30, self.min60, self.daily, self.weekly, self.monthly]
        
        # When onestop_stock gets inputs from other functions, 
        # such as _find_volitility(), with a tuple return value
        # it has to be indexed and peel out the outermost bracket as follows.
        if type(stocks[0]) != str:
            stocks = stocks[0]       
  
        for chart_func in chart_funcs:
            # In case 'qty' is input without the 'qty=5' form,
            # qty will be in the list of stocks as its last element.
            # In that case, the last element in the stocks list will be read as qty
            if type(stocks[-1]) == int:
                for stock in stocks[:-1]:
                    chart_func(stock)
            print('\n')
        
        while True:           
            if len(self.tr_data['charts'].keys()) == len(chart_funcs)*len(stocks):
                break        

        # In case 'qty' is input without the 'qty=5' form,
        # qty will be in the list of stocks as its last element.
        # In that case, the last element in the stocks list will be read as qty        
        if type(stocks[-1]) == int:
            self._auto_fast_orders(stocks[-1])
        else:
            self._auto_fast_orders(qty)  

        with sqlite3.connect('test_tr_data.db') as file:
            for category in self.tr_data.keys():
                for df_name in self.tr_data[category].keys():
                    self.tr_data[category][df_name].to_sql(df_name, file, if_exists='replace')         

        self._event_loop_exec('tr')

    def _find_volitility(self):
        self.priceup()
        # self.pricedown()
        self.volumeup()
        self.poc()

        # column = {'가격급등락':['급등률'], '거래량급증':['급증률'], '매물대집중':['등락률']}
        column = {'가격급등락':['급등률'], '거래량급증':['급증률']}        
        stocks = {}
        ideal = set() # any stocks that fall in both the categories, 가격급등락, 거래량급증
        seen = set()
        for df_name, df in self.tr_data['volitility'].items():
            self.tr_data['volitility'][df_name][column[df_name]] = self.tr_data['volitility'][df_name][column[df_name]].astype('float')
            self.tr_data['volitility'][df_name].sort_values(column[df_name], ascending=False, inplace=True)
            stocks[df_name] = self.tr_data['volitility'][df_name]['종목명'][:5]
            for stock in stocks[df_name]:
                if stock in seen:
                    ideal.add(stock)
                else:
                    seen.add(stock)
        # returns a tuple of 
        # 'ideal', which is a list of stocks 가격급등락, 거래량급증, 매물대집중 all have
        # 'stocks', which consists of top 15 stocks for 가격급등락, 거래량급증, 매물대집중 as a dictionary,
        return ideal, stocks
    
    def onestop_volitility(self, qty=1):
        stocks = self._find_volitility()
        # In case there exist any stock 가격급등락, 거래량급증, 매물대집중 are all met,
        # target_stocks we will analyze will be those stocks, 
        # which are in stocks[0] that returned from _find_volitility()
        # In case the above conditions are not met,
        # target_stocks will be the top 15 stocks for 거래량급증
        # which are in stocks[1]['거래량급증']
        if len(stocks[0]):
            target_stocks = stocks[0]
            print(f'\n거래량급증, 가격급등, 매물대집중 모두 충족하는 종목 {len(target_stocks)}개 발견. 해당종목 분석.\n')
        else:
            target_stocks = stocks[1]['거래량급증']            
            print(f'\n거래량급증, 가격급등, 매물대집중 모두 충족하는 종목 미발견. 거래량급증 상위{len(target_stocks)} 분석.\n')
        
        self.onestop_stock(target_stocks, qty=qty)    
                        
app = QApplication(sys.argv)

kiwoom = Kiwoom()

# type(kiwoom.account_num)

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
# mass('LG에너지솔루션, SK텔레콤, 현대차')
# kiwoom.request_real_chart('현대차', '삼성전자', 'LG에너지솔루션')
# kiwoom.onestop_stock('현대차', '삼성전자', 'LG에너지솔루션')
kiwoom.onestop_volitility()
