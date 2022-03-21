from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import sys

class Kiwoom_Connect(QAxWidget):
    def __init__(self):
        super().__init__()
        self._ProgID_transfer_to_QAxWidget_object()
        self.set_signal_slots()

    def _ProgID_transfer_to_QAxWidget_object(self):
        self.setControl('KHOPENAPI.KHOpenAPICtrl.1')
    
    def comm_connect(self):
        self.dynamicCall('CommConnect()')
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()
    
    def set_signal_slots(self):
        self.OnEventConnect.connect(self._connect_event_slot)
    
    def _connect_event_slot(self, errcode):
        if errcode == 0:
            print('Successfully Connected.')
        elif errcode == 100:
            print('Failed to Exchange User Information. Disconnected.')
        elif errcode == 101:
            print('Failed to Connect to the Server. Disconnected.')
        elif errcode == 102:
            print('Failed to Process Update Information. Disconnected.')
        else:
            print('For Unknown Reasons, disconnected.')

        self.login_event_loop.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    kiwoom = Kiwoom_Connect()
    kiwoom.comm_connect()
    app.exec_()

    
