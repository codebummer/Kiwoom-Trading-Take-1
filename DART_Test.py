import requests
import sqlite3
import pandas as pd
from cert_key import *

url = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'
params = {
    'crtfc_key' : CERT_KEY,
    'corp_code' : '00126380',
    'bsns_year' : '2018',
    'reprt_code' : '11011'
}
with requests.get(url, params) as response:
    print('Successfully downloaded data from the API request')
df = pd.DataFrame.from_dict(response.json()['list'])

with sqlite3.connect('D:/myProjects/myKiwoom/DART_Test.db') as connection:
    print('Successfully connected to DART_Test.db')

df.to_sql('Single Business Major Accounts', connection)
print('Data successfully archived in the database')
