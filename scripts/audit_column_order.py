#!/usr/bin/env python3
"""Audit every migrated table for column-ORDER mismatches between source and
destination.

migrate.py used plain `mysqldump` (positional INSERTs) for most tables. A
positional INSERT only aligns correctly when both schemas list their columns in
the same ordinal order. When the column *count* matches but the *order* differs,
MySQL happily inserts the row and silently writes each value into the wrong
column. That is how oc_tables_columns ended up with usergroup_default='0'.

This script reports, for each table present on both servers:
  MISMATCH  - same column set, different ordinal order  -> data is shifted
  COUNT     - different column count
  OK        - identical ordering
"""

import os
import subprocess
import sys

OLD_DB = "nextcloud"
OLD_USER = "nextcloud"
NEW_DB = "sql_cloud_amarisstock_com"
NEW_USER = "sql_cloud_amarisstock_com"
NEW_HOST = "164.68.104.123"


def old_query(sql: str) -> list[str]:
    result = subprocess.run(
        ["mysql", "-u", OLD_USER, f"-p{os.environ['OLD_DB_PASS']}",
         "-h", "127.0.0.1", OLD_DB, "-N", "-B", "-e", sql],
        capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def new_query(sql: str) -> list[str]:
    remote = (
        f"mysql -u {NEW_USER} -p'{os.environ['NEW_DB_PASS']}' "
        f"-h 127.0.0.1 {NEW_DB} -N -B -e \"{sql}\""
    )
    result = subprocess.run(
        ["sshpass", "-p", os.environ["NEW_SSH_PASS"], "ssh",
         "-o", "StrictHostKeyChecking=no", f"root@{NEW_HOST}", remote],
        capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def columns_by_table(rows: list[str]) -> dict[str, list[str]]:
    tables: dict[str, list[str]] = {}
    for line in rows:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        table, column = parts[0], parts[1]
        tables.setdefault(table, []).append(column)
    return tables


def main() -> int:
    order_sql_old = (
        "SELECT table_name, column_name FROM information_schema.columns "
        f"WHERE table_schema='{OLD_DB}' ORDER BY table_name, ordinal_position;"
    )
    order_sql_new = (
        "SELECT table_name, column_name FROM information_schema.columns "
        f"WHERE table_schema='{NEW_DB}' ORDER BY table_name, ordinal_position;"
    )

    old = columns_by_table(old_query(order_sql_old))
    new = columns_by_table(new_query(order_sql_new))

    shared = sorted(set(old) & set(new))
    mismatched: list[tuple[str, list[tuple[int, str, str]]]] = []
    count_diff: list[str] = []

    for table in shared:
        old_cols, new_cols = old[table], new[table]
        if len(old_cols) != len(new_cols):
            count_diff.append(table)
            continue
        if old_cols == new_cols:
            continue
        if set(old_cols) != set(new_cols):
            count_diff.append(table)
            continue
        diffs = [
            (i + 1, o, n)
            for i, (o, n) in enumerate(zip(old_cols, new_cols))
            if o != n
        ]
        mismatched.append((table, diffs))

    print(f"tables on both servers: {len(shared)}")
    print(f"column-ORDER mismatches (data silently shifted): {len(mismatched)}")
    print(f"column-SET/count differences: {len(count_diff)}")
    print()

    if mismatched:
        print("=" * 72)
        print("ORDER MISMATCH - positional INSERT wrote values into wrong columns")
        print("=" * 72)
        for table, diffs in mismatched:
            rows = new_query(f"SELECT COUNT(*) FROM {table};")
            n = rows[0] if rows else "?"
            print(f"\n{table}  ({n} rows on destination, {len(diffs)} positions differ)")
            for pos, o, c in diffs:
                print(f"    pos {pos:>2}: source '{o}'  ->  destination '{c}'")

    if count_diff:
        print()
        print("=" * 72)
        print("COLUMN SET / COUNT DIFFERENCES (need explicit-column import)")
        print("=" * 72)
        for table in count_diff:
            only_old = sorted(set(old[table]) - set(new[table]))
            only_new = sorted(set(new[table]) - set(old[table]))
            print(f"\n{table}: source={len(old[table])} dest={len(new[table])}")
            if only_old:
                print(f"    only on source     : {', '.join(only_old)}")
            if only_new:
                print(f"    only on destination: {', '.join(only_new)}")

    return 1 if mismatched else 0


if __name__ == "__main__":
    for var in ("OLD_DB_PASS", "NEW_DB_PASS", "NEW_SSH_PASS"):
        if var not in os.environ:
            print(f"missing env var {var}", file=sys.stderr)
            sys.exit(2)
    sys.exit(main())
