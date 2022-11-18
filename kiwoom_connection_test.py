from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import sys
import sqlite3

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
        # self.QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')

        self.comm_connect()
        # self.signal_slot_event_handlers()

    def comm_connect(self):
        self.dynamicCall('CommConnect()')
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()
    
    # def signal_slot_event_handlers(self):

    def set_input_values(self, id, value):
        self.dynamicCall('SetInputValue(QString, QString)', id, value)
    
    def comm_req_data(self, rqname, trcode, pre_next, screen_no):
        self.dynamicCall('CommRqData(QString, QString, int, QString)', rqname, trcode, pre_next, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()
    
    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, pre_next, data_length, errcode, message, splmmsg):
        if pre_next == '2':
            self.remaining_data = True
        else:
            self.remaining_data = False
        

        

        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    app.exec_()

