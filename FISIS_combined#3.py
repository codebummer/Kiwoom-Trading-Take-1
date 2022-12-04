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
banks = ongoings.reset_index()
# banks[banks['finance_nm'].str.contains('농심캐피탈')]
# banks[banks['finance_nm'].str.contains('현대투자파트너스')]
# banks.drop(list(range(79,161)), inplace=True)
# banks[banks['finance_nm'].str.contains('교보생명')]
# banks.drop(columns='level_0', inplace=True)

# with sqlite3.connect('bank_transit.db') as file:
#     banks.to_sql('banks_transit', file, if_exists='append')

# banks.drop([345], inplace=True)
# banks.drop(list(range(381,419)), inplace=True)
# banks = banks[~banks['finance_nm'].str.contains('한국지점')]

# select banks to search
major=pd.DataFrame()
screen = lambda x:major.append(banks[banks['finance_nm'].str.contains(x)])
picks = ['국민', '신한', '우리', '하나','KB', '외환', '산업', '기업', '카카오', '신협', '축협', '농협','수협', '새마을']
for pick in picks:
    major = screen(pick)
major.reset_index(inplace=True)

# select stats to process
# focusstats = pd.DataFrame()
# add = lambda x:focusstats.append(x)
# get = [[28,36], [39,44], [56,58], [67, 72], [84, 92], [707, 724]]
# for focus in get:
#     if len(focus) == 1:
#         focusstats = add(stats.loc[focus])
#     else:
#         for idx in list(range(focus[0], focus[1])):
#             focusstats = add(stats.loc[idx])
            
focusstats = pd.DataFrame()
screen = lambda x:focusstats.append(stats[stats['list_nm'].str.contains(x)])
picks = ['자산건전성', '자본적정성', '여신건전성', '유동성', '자금조달', '대출금 운용', '여신건전성', '연채율', 'BIS', '부실채권', '용도별 대출채권', '업종별 대출금']
for pick in picks:
    focusstats = screen(pick)            
focusstats.reset_index(inplace=True)

# select accounts to process
# finaccounts = accounts.loc[711:1326]
finaccounts = accounts.loc[1285:1326]
finaccounts.reset_index(inplace=True)

archive = {'id':[], 'name':[], 'data':[]}
url = 'http://fisis.fss.or.kr/openapi/statisticsInfoSearch.json'
for fid, fincode in enumerate(major['finance_cd']):
    print('processing finance code: ', major['finance_nm'][fid])
    for statid, lst in enumerate(focusstats['list_no']):
        print('processing stat list: ', focusstats['list_nm'][statid])
        for accid, account in enumerate(finaccounts['account_cd']):
            print('processing account: ', finaccounts['account_nm'].values[accid])
            params = {
                'auth' : api_key, 
                'financeCd' : fincode, 
                'listNo' : lst,  
                'accountCd' : account,
                'lang' : 'kr',
                'term' : 'Q',
                'startBaseMm' : '202207',
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
                    archive['data'].append(add)

with open('temp_result.json', 'w') as file:
    json.dump(archive, file)
