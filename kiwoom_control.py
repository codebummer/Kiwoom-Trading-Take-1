from get_kiwoom_connection import *

if __name__ == '__main__':
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    app.exec_()
