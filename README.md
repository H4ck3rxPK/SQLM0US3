# SQLM0US3
🐹 A self-learning scripting project inspired by the SQLME0w. It’s still in early stages with only a few versions and is being developed. Feel free to use it if you need.

## Sample Command
```python
python3 SQLM0US3_xx.py http://sample.com
HTB_ACADEMY_ORACLE
(1) Get Length
(2) Get Name
Your Option : 
```

You can type a number to choose a mode:

``1``: just enter only sql syntax, such as
```sql
LEN(DB_NAME())

SELECT COUNT(*) FROM information_schema.tables WHERE table_catalog='d4y'

SELECT column_name FROM information_schema.columns WHERE table_catalog='d4y' AND table_name = 'users'
```

``2``: just enter only sql syntax and the length in the end
```sql
SELECT table_name FROM information_schema.tables WHERE table_catalog='d4y' 3
```


