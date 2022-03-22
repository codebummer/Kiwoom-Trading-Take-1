import zipfile, io
import urllib.request
from cert_key import *

url = 'https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key='
param = CERT_KEY

with urllib.request.urlopen(url+param) as response:
    with zipfile.ZipFile(io.BytesIO(response.read())) as zip:
        zip.extractall('corpCode')
        print('All Business List Successfully Received')
