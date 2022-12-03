import requests, sqlite3, json, os, sys
import pandas as pd
sys.path.append(r'D:\myprojects\TradingDB')
os.chdir(r'D:\myprojects\TradingDB')
from fisis_key import *

with sqlite3.connect('allbanks.db') as file:
    allbanks = pd.read_sql('SELECT * FROM [Banks]', file)
with sqlite3.connect('stats.db') as file:
    stats = pd.read_sql('SELECT * FROM [Stats]', file)
with sqlite3.connect('accounts.db') as file:
    accounts = pd.read_sql('SELECT * FROM [Accounts]', file)

ongoings = allbanks.loc[~allbanks['finance_nm'].str.contains('[폐]', case=False)]

archive = {'index':[], 'description':[], 'data':[]}
count = 0
# archive = []
url = 'http://fisis.fss.or.kr/openapi/statisticsInfoSearch.json'
for fincode in ongoings['finance_cd']:
    for lst in stats['list_no']:
        for account in accounts['account_cd']:
            params = {
                'auth' : api_key, 
                'financeCd' : fincode, 
                'listNo' : lst,  
                'accountCd' : account,
                'lang' : 'kr',
                'term' : 'Q',
                'startBaseMm' : '201801',
                'endBaseMm' : '202211'
                }            
            with requests.get(url, params) as response:
                replyjson = response.json()
                archive['index'].append(count)
                archive['description'].append([replyjson['result']['description']])
                                
                add = {}
                for key in replyjson['result']['list'][0].keys():
                    add[key] = []
                for elem in replyjson['result']['list']:
                    for key, value in elem.items():
                        add[key].append(value)                                   
                archive['data'].append([add])
                # archive.append(add)
                
                count += 1



with open('temp_result.json', 'w') as file:
    json.dump(archive, file)

