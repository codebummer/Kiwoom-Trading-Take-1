import json, os, sqlite3, requests
import pandas as pd
from all_banks_fisis_api_key import *

os.chdir(r'D:\myprojects\TradingDB')

lrgs = 'AJHIFWGXDCKTNEOQPSMLBR'
smls = 'ABCDPEF'
path = 'http://fisis.fss.or.kr/openapi/statisticsListSearch.json'
# params = {'auth' : api_key, 'lrgDiv' : lrg, 'smlDiv' : sml, 'lang' : 'kr'}

banks = {}
for lrg in lrgs:
    params = {'auth' : api_key, 'lrgDiv' : lrg, 'lang' : 'kr'}
    with requests.get(path, params) as response:
        replyjson = response.json()
        banks[lrg] = replyjson

with open('stats.json', 'w') as file:
    json.dump(banks, file)

allbanks = {'lrg_div_nm':[], 'sml_div_nm':[], 'list_no':[], 'list_nm':[]}
for lrg in lrgs:
    for bank in banks[lrg]['result']['list']:
        for key, value in bank.items():
            allbanks[key].append(value)
df = pd.DataFrame(allbanks)
with sqlite3.connect('stats.db') as file:
    df.to_sql('Stats', file, if_exists='append')
