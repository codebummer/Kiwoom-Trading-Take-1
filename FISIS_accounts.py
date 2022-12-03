import requests, sqlite3, json, os, sys
import pandas as pd

sys.path.append(r'D:\myprojects\TradingDB')
from fisis_key import *
os.chdir(r'D:\myprojects\TradingDB')

with sqlite3.connect('stats.db') as file:
    stats = pd.read_sql('SELECT * FROM [Stats]', file)

accounts = {'list_no':[], 'list_nm':[], 'account_cd':[], 'account_nm':[]}
url = 'http://fisis.fss.or.kr/openapi/accountListSearch.json'
for idx in range(len(stats)):
    params = {'auth' : api_key, 'listNo' : stats.loc[idx, 'list_no'], 'lang' : 'kr'}
    with requests.get(url, params) as response:
        replyjson = response.json()
        for dict in replyjson['result']['list']:
            for key, value in dict.items():
                accounts[key].append(value)

df = pd.DataFrame(accounts)
with sqlite3.connect('accounts.db') as file:
    df.to_sql('Accounts', file, if_exists='append')        
