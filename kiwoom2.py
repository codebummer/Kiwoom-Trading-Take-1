from distutils import errors
from pickle import TRUE
from kiwoom1 import *
import pandas as pd
import time
import sqlite3
import matplotlib.pyplot as plt

class tr_requests(Kiwoom):
    def __init__(self):
        super().__init__()
        self.set_comm_request_data_signal_slot()
   
    def set_input_value(self, id, value):
        self.dynamicCall('SetInputValue(QString, QString)', id, value)
    
    def comm_request_data(self, rqname, trcode, prenext, scrno):
        self.dynamicCall('CommRqData(QString, QString, int, QString)', rqname, trcode, prenext, scrno)
        self.data_request_loop = QEventLoop()
        self.data_request_loop.exec_()
    
    def set_comm_request_data_signal_slot(self):
        self.OnReceiveTrData.connect(self._receive_tr_data)
    
    def _receive_tr_data(self, scrno, rqname, trcode, recordname, prenext, datalen, errcode, msg, splm_msg):
        if prenext == 2:
            self.remaining_data = True
        else:
            self.remaining_data = False

        if trcode == 'opt10081':
            self.results_df = self._opt_10081(trcode, recordname)

        try:
            self.data_request_loop.exit()            
        except AttributeError as e:
            raise e            

    def get_comm_data_slot(self, trcode, recordname, index, itemname):
        return self.dynamicCall('GetCommData(QString, QString, int, QString)', trcode, recordname, index, itemname).strip()

    def _get_repeat_cnt(self, trcode, recordname):
        return self.dynamicCall('GetRepeatCnt(QString, QSTring)', trcode, recordname)

    def get_item_names(self):
        return ['일자', '시가', '고가', '저가', '현재가', '거래량', '거래대금']
    
    def _opt_10081(self, trcode, recordname):
        _index = self._get_repeat_cnt(trcode, recordname)
        _itemnames = self.get_item_names()
        _opt_10081_df = pd.DataFrame([])
        for item in _itemnames:  
            results_sub = []
            for itemnum in range(_index):            
                # Do not use strip() here as in self.get_comm_data_slot(trcode, recordname, itemnum, item).strip()
                # because self.get_comm_data_slot(trcode, recordname, itemnum, item) is returned as an object
                # strip() cannot function on the returned form.
                # Instead, use strip() directly on the returned value of GetCommData
                # strip() can function on that form. 
                results_sub.append(self.get_comm_data_slot(trcode, recordname, itemnum, item)) 
            _opt_10081_df[item] = results_sub
        _opt_10081_df = _opt_10081_df.set_index('일자')
        print(f'Results for requests are as follows:\n', _opt_10081_df)
        return _opt_10081_df

TR_REQ_TIME_INTERVAL = 0.2

def inputs(self, id_value_pairs):
    for id in id_value_pairs:
        self.set_input_value(id, id_value_pairs[id])

opt_10081_set_inputs = {
    '종목코드' : '005930',
    '기준일자' : '20220325',
    '수정주가구분' : 1
}

opt_10081_comm_inputs = ['rq_opt10081', 'opt10081', 0, '0001']

def comm_requsts_handler(self, set_inputs, comm_inputs):
    # perform the first request without checking if remaining_data is true 
    # since it is not instantiated before the first CommTrData response is received
    inputs(self, set_inputs)
    self.comm_request_data(*comm_inputs)

    while self.remaining_data == True:
        time.sleep(TR_REQ_TIME_INTERVAL)
        inputs(self, set_inputs)
        self.comm_request_data(*comm_inputs)

def db_factory(dbname):
    return sqlite3.connect('D:/myProjects/myKiwoom/'+dbname)

def df_to_db(df, dbname, table):
    try:
        db = db_factory(dbname)
        print('connected to db')
    except Error as e:
        print(e)
    
    try:
        df.to_sql(table, db, if_exists = 'replace')
        print('saved requested data in db')
    except Error as e:
        print(e)
    

if __name__ == '__main__':
    transaction_req = tr_requests()
    comm_requsts_handler(transaction_req, opt_10081_set_inputs, opt_10081_comm_inputs)
    df_to_db(transaction_req.results_df, 'daily_records.db', 'Daily Prices')
    plt.plot(transaction_req.results_df['현재가'].head())
    plt.show()

    
    


