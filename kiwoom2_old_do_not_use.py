from kiwoom1 import *
import pandas as pd

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
        self.OnReceiveTrData.connect(self.get_comm_data_slot)

    def get_comm_data_slot(self, scrno, rqname, trcode, recordname, prenext, datalen, errcode, msg, splm_msg):
        _index = self.get_repeat_cnt(trcode, recordname)
        _itemnames = self.get_item_names()
        df = pd.DataFrame([])
        for item in _itemnames:  
            results_sub = []
            for itemnum in range(_index):            
                results_sub.append(self.dynamicCall('GetCommData(QString, QString, int, QString', trcode, recordname, itemnum, item).strip())
            df[item] = results_sub
        print(f'Results for requests are as follows:\n', df)
        self.data_request_loop.exit()

    def get_repeat_cnt(self, trcode, recordname):
        return self.dynamicCall('GetRepeatCnt(QString, QSTring)', trcode, recordname)

    def get_item_names(self):
        return ['현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가']

def inputs(self, id_values):
    for id in id_values:
        self.set_input_value(id, id_values[id])

daily = {
    '종목코드' : '005930',
    '기준일자' : '20220325',
    '수정주가구분' : '1'
}

comm_inputs = ['RQ', 'opt10081', '0', '0001']

def comm_handler(self, comm_inputs):
    self.comm_request_data(*comm_inputs)

if __name__ == '__main__':
    transaction_req = tr_requests()
    inputs(transaction_req, daily)
    # transaction_req.comm_request_data(*comm_inputs)
    comm_handler(transaction_req, comm_inputs)


    


