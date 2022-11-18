from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import sys
# from abc import ABC, abstractclassmethod

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self._ProgID_handover_to_QAxWidget()
        self.set_comm_connect_signal_slots()
        self.comm_connect()
        # when comm_connect() is called before set_signal_slots(), 
        # following procedures will not work.
        

    def _ProgID_handover_to_QAxWidget(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
    
    def comm_connect(self):
        self.dynamicCall('CommConnect()')
        self.login_loop = QEventLoop()
        self.login_loop.exec_()
    
    def set_comm_connect_signal_slots(self):
        self.OnEventConnect.connect(self._comm_connect_slot)
    
    def _comm_connect_slot(self, err):
        if err == 0:
            print('connected')
        else:
            print('disconnected')
        
        self.login_loop.exit()
        print('login loop exited')
    
 
    
# if __name__ == '__main__':
app = QApplication(sys.argv)
# kiwoom = Kiwoom()
    


