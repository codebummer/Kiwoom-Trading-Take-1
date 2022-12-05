from pywinauto import application, timings
import time, os

os.chdir(r'D:\myprojects\TradingDB')
from kiwoomkeys import *

app = application.Application()
app.start(r'C:\KiwoomFlash3\Bin\NKMiniStarter.exe')

title = '번개3 Login'
dlg = timings.wait_until_passes(20, 0.5, lambda: app.window(title=title))

pass_ctrl = dlg.Edit2
pass_ctrl.set_focus()
pass_ctrl.type_keys(key)

cert_ctrl =dlg.Edit3
cert_ctrl.set_focus()
cert_ctrl.type_keys(cert)

btn_ctrl = dlg.Button0
btn_ctrl.click()

time.sleep(60)
os.system('taskkill /im nkmini.exe')
