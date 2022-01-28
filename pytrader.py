import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
from Kiwoom import *

os.chdir('D:/Documents/02 IT/01 Coding/04 My Projects/05 My pyKiwoom1')
trading_window = uic.loadUi('pytrader_window.ui')

class MyWindow(QMainWindow, trading_window):
    def __init__(self):
        super.__init__()

        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()

        self.kiwoom.req_tr_data()

        self.kiwoom.send_order()

    def yield_rate(self):


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()







