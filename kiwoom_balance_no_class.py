from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from TradingDB.kiwoompersonal import *
import sys

app = QApplication(sys.argv)
ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')


def logcheck(err):
    if err == 0:
        print('Logged in')
        log_loop.quit()
ocx.OnEventConnect.connect(logcheck)

def tr_receiver(scrno, rqname, trcode, recordname, prenext, unused1, unused2, unused3, unused4):
    if rqname == 'OPW00001':
        cnt = ocx.dynamicCall('GetRepeatCnt(QString, QString)', trcode, recordname)
        print(f'{cnt} data received')
        add = {}
        for output in opw00001['outputs']:
            get = ocx.dynamicCall('GetCommData(QString, QString, int, QSTring)', trcode, rqname, 0, output).strip()            
            get = int(get)
            get = f'{get:,}'
            add[output] = get
        print(f'{add}')
    tr_loop.quit()
ocx.OnReceiveTrData.connect(tr_receiver)


ocx.dynamicCall('CommConnect')
log_loop = QEventLoop()
log_loop.exec_()

account_num = ocx.dynamicCall('GetLoginInfo(QString)', ['ACCNO']).strip(';')

opw00001 = {'inputs': {'계좌번호':account_num, '비밀번호':password, '비밀번호입력매체구분':'00', '조회구분':'2'},
            'outputs': ['예수금', '주문가능금액', 'd+2출금가능금액']}
for tr_name, tr_value in opw00001['inputs'].items():
    ocx.dynamicCall('SetInputValue(QString, QString)', tr_name, tr_value)
ocx.dynamicCall('CommRQData(QString, QString, int, QString)', 'OPW00001', 'opw00001', '0', '0001')
tr_loop = QEventLoop()
tr_loop.exec_()
