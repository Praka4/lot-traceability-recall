import argparse
import csv
import json
import sqlite3
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="output/traceability.db")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    out_dir = Path(args.out)
    csv_dir = out_dir / "csv"
    json_dir = out_dir / "json"
    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(args.db)
    try:
        exports = {
            "recallscope": "RecallScope",
            "recallaction": "RecallAction",
        }

        for filename, table in exports.items():
            cursor = con.execute(f"SELECT * FROM {table}")
            columns = [item[0] for item in cursor.description]
            rows = cursor.fetchall()

            with open(csv_dir / f"{filename}.csv", "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(columns)
                writer.writerows(rows)

            records = [dict(zip(columns, row)) for row in rows]
            with open(json_dir / f"{filename}.json", "w", encoding="utf-8") as file:
                json.dump(records, file, indent=2, ensure_ascii=False, default=str)

            print(f"{table}: exported {len(rows)} rows to CSV and JSON")
    finally:
        con.close()

if __name__ == "__main__":
    main()
