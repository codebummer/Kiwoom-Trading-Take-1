from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys

def login_result(err):
    if err == 0:
        print('connected')
    login_loop.quit()

app = QApplication(sys.argv)
ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')

ocx.OnEventConnect.connect(login_result)
ocx.dynamicCall('CommConnect()')
login_loop = QEventLoop()
login_loop.exec_()
