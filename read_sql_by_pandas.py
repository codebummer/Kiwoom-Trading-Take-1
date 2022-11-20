import sqlite3
import pandas as pd

file = sqlite3.connect(r'D:\myprojects\TradingDB\900310_Tick.db')
# To read from sql by pandas you have to include the table name with square brackets
df = pd.read_sql('SELECT * FROM [900310_Tick]', file) 
# Rename the columns
df.columns = ['Index', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount']
