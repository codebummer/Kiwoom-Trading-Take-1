


class Kiwoom:
    def __init__(self):
        super.__init__()

        self.setControl('KHOPENAPI.KHOpenAPICtrl.1') #Instantiate a Kiwoom class to use the OCX control.

        self._comm_connect()
        self._event_handlers()
    
    def _comm_connect(self): #Connect and Log in to Kiwoom OPEN API
        self.dynamicCall('CommConnect()')
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    
    def _event_handlers(self): #Creating event loops        
        self.OnEventConnect.connect(self._on_event_connect)
        self.OnReceiveTrData.connect(self._received_tr_data_handlers)


    def _on_event_connect(self, err):
        if err == 0:
            print('Successfully Logged-in')
        else:
            print('Log-in Failed')

        self.login_event_loop.exit()

    def req_tr_data(self, rqname, trcode, prev_next, screen_no): #Make transaction requests to the Kiwoom server.
        # self.set_input_values(id, value) #Pass along inputs required to make transaction requests
        self.dynamicCall('CommRqData(QString, QString, int, QString)', rqname, trcode, prev_next, screen_no)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    
    def set_input_values(self, id, value): #Pass along inputs required to make transaction requests
        self.dynamicCall('SetInputValue(Qstring, Qstring)', id, value)

    
    def send_orders(self): #Making order requests to the Kiwoom server.

    def _received_tr_data_handlers(self, screen_no, rqname, trcode, record_name, pre_next, unused1, unused2, unused3, unused4):
        if pre_next == 2:
            self.continued_data = True
        else:
            self.continued_data = False
        
        if rqname = 

        try:
            self.tr_event_loop.exit()
        except AttributeError:
            print(AttributeError)


    # pick up where I left off: look for methods to handle specific transactions.

    


        

