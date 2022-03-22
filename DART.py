import zipfile, io, requests
# import urllib.request
from cert_key import *

# url = 'https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key='
url = 'https://opendart.fss.or.kr/api/corpCode.xml'
param = CERT_KEY

# with urllib.request.urlopen(url+param) as response:
#     with zipfile.ZipFile(io.BytesIO(response.read())) as zip:
#         zip.extractall('corpCode')
#         print('All Business List Successfully Received')


with requests.get(url, params = param) as response:
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip:
        # response.content shows it contains bytes strings. 
        # However, it shows it is not in a zip format, but in a XML format
        # So, make a statement to handle response as a XML format
        print('All Business List Successfully Received')

