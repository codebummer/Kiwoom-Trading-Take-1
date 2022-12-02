
import requests, json, os, sqlite3
import pandas as pd
from all_banks_fisis_api_key import *
os.chdir(r'D:\myprojects\TradingDB')

parts = 'AFDNPBJWCESRHGKOM'
path = 'http://fisis.fss.or.kr/openapi/companySearch.json'

allbanks = {}
for part in parts:
    params = {'auth' : api_key, 'partDiv' : part, 'lang' : 'kr'}
    with requests.get(path, params) as response:
#         byte = response.content
        replyjson = response.json()
        allbanks[part] = replyjson

# with open('banks.json', 'w') as file:
#     json.dump(allbanks, file)

allbanksmix = {}
count = 0
for part in parts:
    for values in allbanks[part]['result']['list']:       
        allbanksmix[count] = values
        count += 1

# with open('banksmix.json', 'w') as file:
#     json.dump(allbanksmix, file)

allbanksmix = [bank for bank in allbanksmix.values()]
alldf = {'finance_cd':[], 'finance_nm':[], 'finance_path':[]}
for bank in allbanksmix:
    for key, value in bank.items():
        alldf[key].append(value)

df = pd.DataFrame(alldf)
with sqlite3.connect('allbanks.db') as file:
    df.to_sql('Banks', file, if_exists='append')
