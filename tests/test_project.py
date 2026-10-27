import sqlite3, subprocess, sys, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_generator_and_foreign_keys(tmp_path):
    out=tmp_path/"out"
    subprocess.run([sys.executable,str(ROOT/"src/generate.py"),"--out",str(out),"--scale","starter","--seed","20261022"],check=True)
    con=sqlite3.connect(out/"traceability.db")
    assert con.execute("SELECT COUNT(*) FROM Supplier").fetchone()[0]==25
    assert con.execute("SELECT COUNT(*) FROM MaterialLot").fetchone()[0]==250
    assert con.execute("PRAGMA foreign_key_check").fetchall()==[]
    assert con.execute("SELECT COUNT(*) FROM GroundTruth").fetchone()[0]>0
    con.close()

def test_recall_simulator_runs(tmp_path):
    out=tmp_path/"out"
    subprocess.run([sys.executable,str(ROOT/"src/generate.py"),"--out",str(out),"--scale","starter"],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable,str(ROOT/"src/simulate_recall.py"),"--db",str(out/"traceability.db"),"--out",str(out)],check=True)
    assert (out/"recall_metrics.json").exists()


def test_recall_detects_missing_customer_notification(tmp_path):
    import json

    out = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/generate.py"),
            "--out", str(out),
            "--scale", "starter",
            "--seed", "20261022",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/simulate_recall.py"),
            "--db", str(out / "traceability.db"),
            "--out", str(out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    with open(out / "recall_metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)

    recall = next(
        item for item in metrics
        if item["recall_id"] == "REC-2026-000001"
    )

    assert recall["affected_customers"] == 3
    assert recall["missing_notification_count"] == 1
    assert recall["missing_notification_customer_ids"] == "CUST-00200"
 
def test_detects_delivery_exceeding_production(tmp_path):
    out = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/generate.py"),
            "--out", str(out),
            "--scale", "starter",
            "--seed", "20261022",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    con = sqlite3.connect(out / "traceability.db")

    row = con.execute(
        """
        SELECT d.delivery_id,
               d.quantity_delivered,
               f.quantity_produced
        FROM Delivery d
        JOIN FinishedLot f
          ON d.finished_lot_id = f.finished_lot_id
        WHERE d.delivery_id = 'DEL-0000001'
        """
    ).fetchone()

    con.close()

    assert row is not None
    delivery_id, delivered, produced = row

    assert delivery_id == "DEL-0000001"
    assert delivered > produced
 
def test_validator_reports_overdelivery(tmp_path):
    out = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/generate.py"),
            "--out", str(out),
            "--scale", "starter",
            "--seed", "20261022",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/validate.py"),
            "--db", str(out / "traceability.db"),
            "--out", str(out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    report_path = out / "validation_summary.json"
    assert report_path.exists()
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    assert report["delivery_over_production"] > 0
    
def test_validator_reports_missing_input_lot(tmp_path):
    out = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/generate.py"),
            "--out", str(out),
            "--scale", "starter",
            "--seed", "20261022",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "src/validate.py"),
            "--db", str(out / "traceability.db"),
            "--out", str(out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    with open(
        out / "validation_summary.json",
        encoding="utf-8",
    ) as f:
        report = json.load(f)

    issue_rows = report["issue_rows"]

    missing_lot_detected = any(
        row[0] == "FinishedLot"
        and row[1] == "MISSING_INPUT_LOT"
        and row[2] > 0
        for row in issue_rows
    )

    assert missing_lot_detected
