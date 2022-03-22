import requests
import sqlite3
import pandas as pd

url = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'
params = {
    'crtfc_key' : '1a466b948211ddfe0d373e34d3f7dd39e22439de',
    'corp_code' : '00126380',
    'bsns_year' : '2018',
    'reprt_code' : '11011'
}

response = requests.get(url, params)
df = pd.DataFrame.from_dict(response.json()['list'])

with sqlite3.connect('D:/myProjects/myKiwoom/DART_Test.db') as connection:
    print('Successfully connected to DART_Test.db')

df.to_sql('Single Business Major Accounts', connection)
print('Data successfully archived in the database')
