import zipfile, io
# import requests, json, xmltodict
import urllib.request
from cert_key import *

url = 'https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key='
# url = 'https://opendart.fss.or.kr/api/corpCode.xml'
param = CERT_KEY

with urllib.request.urlopen(url+param) as response:
    with zipfile.ZipFile(io.BytesIO(response.read())) as zip:
        zip.extractall('corpCode')
        print('All Business List Successfully Received')


# with requests.get(url, params = param) as response:
#     with zipfile.ZipFile(io.BytesIO(response.content)) as xml_form:
#         json_form = xmltodict.parse(xml_form)
#         json_data = json.dumps(json_form)
#         with open('corpCode.json', 'w') as json_file:
#             json_file.write(json_data)
#         # response.content shows it contains bytes strings. 
#         # However, it shows it is not in a zip format, but in a XML format
#         # So, make a statement to handle response as a XML format
#         print('All Business List Successfully Received')
