# from urllib.request import urlopen
# from urllib.parse import urlencode
from zipfile import ZipFile
import dart_fss as dart
import requests
import sqlite3
import pandas as pd
import os, json
from cert_key import *

os.chdir(r'D:\myprojects\TradingDB')

url = 'https://opendart.fss.or.kr/api/corpCode.xml'
params = {'crtfc_key' : CERT_KEY}
# params = urlencode(params).encode('utf-8')
# with urlopen(url, params) as response:
#     stocklist_bytes = response.read()  
#     print('Successfully downloaded the stock list')


with requests.get(url, params) as response:
    stocklist = ZipFile(response, 'r')

