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
finaccounts = accounts.loc[711:1326]
archive = {'id':[], 'name':[], 'data':[]}
url = 'http://fisis.fss.or.kr/openapi/statisticsInfoSearch.json'
for fid, fincode in enumerate(ongoings['finance_cd']):
    print('processing finance code: ', ongoings['finance_nm'][fid])
    for statid, lst in enumerate(stats['list_no']):
        print('processing stat list: ', stats['list_nm'][statid])
        for accid, account in enumerate(finaccounts['account_cd']):
            print('processing account: ', finaccounts['account_nm'].values[accid])
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
                totalcount = replyjson['result']['total_count']          
                if totalcount != '0':                    
                    archive['id'].append(replyjson['result']['description'][0]['column_id'])
                    archive['name'].append(replyjson['result']['description'][0]['column_nm'])                                    
                    add = {}
                    for key in replyjson['result']['list'][0].keys():
                        add[key] = []
                    for elem in replyjson['result']['list']:
                        for key, value in elem.items():
                            add[key].append(value)                                   
                    # if totalcount == '0':
                    #     continue
                    # elif totalcount == '1':
                    #     archive['data'].append(add)
                    # else:
                    #     for idx in range(int(totalcount)):
                    #         for key in archive['data'][idx].keys():
                    #             archive['data'][idx][key].append(add[key])
                    
                    archive['data'].append(add)

with open('temp_result.json', 'w') as file:
    json.dump(archive, file)
