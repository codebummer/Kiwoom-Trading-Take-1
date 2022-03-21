from get_kiwoom_connection_2 import *

if __name__ == '__main__':
    app = QApplication(sys.argv)
    kiwoom = Kiwoom_Connect()
    kiwoom.comm_connect()
    app.exec_()
