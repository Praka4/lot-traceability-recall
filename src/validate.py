import argparse, sqlite3, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--db",default="output/traceability.db"); ap.add_argument("--out",default="output")
    a=ap.parse_args(); con=sqlite3.connect(a.db); con.execute("PRAGMA foreign_keys=ON")
    checks={}
    checks["foreign_key_violations"]=con.execute("PRAGMA foreign_key_check").fetchall()
    checks["duplicate_primary_keys"]={}
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        info=con.execute(f"PRAGMA table_info({table})").fetchall()
        pk=[r[1] for r in info if r[5]]
        if pk:
            col=pk[0]
            dup=con.execute(f"SELECT {col},COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*)>1").fetchall()
            if dup: checks["duplicate_primary_keys"][table]=dup
    checks["date_order_violations"]=con.execute("SELECT COUNT(*) FROM ProductionOrder WHERE end_date < start_date").fetchone()[0]
    checks["consumption_by_lot_exceeds_received"]=con.execute("""SELECT COUNT(*) FROM MaterialLot m WHERE (SELECT COALESCE(SUM(quantity_consumed),0) FROM MaterialConsumption c WHERE c.material_lot_id=m.material_lot_id)>m.quantity_received""").fetchone()[0]
    checks["delivery_over_production"]=con.execute("""SELECT COUNT(*) FROM (SELECT f.finished_lot_id,f.quantity_produced,SUM(d.quantity_delivered) total FROM FinishedLot f JOIN Delivery d USING(finished_lot_id) GROUP BY f.finished_lot_id HAVING total>f.quantity_produced)""").fetchone()[0]
    checks["available_recalled_inventory"]=con.execute("""SELECT COUNT(*) FROM Inventory i JOIN FinishedLot f USING(finished_lot_id) WHERE f.status='RECALLED' AND i.sale_status='AVAILABLE'""").fetchone()[0]
    checks["issue_rows"]=con.execute("""SELECT 'FinishedLot' entity,issue_type,COUNT(*) n FROM FinishedLot WHERE issue_type IS NOT NULL GROUP BY issue_type UNION ALL SELECT 'Delivery',issue_type,COUNT(*) FROM Delivery WHERE issue_type IS NOT NULL GROUP BY issue_type""").fetchall()
    checks["pass_fk_integrity"]=not checks["foreign_key_violations"]
    checks["pass_primary_key_uniqueness"]=not checks["duplicate_primary_keys"]
    checks["interpretation"]="Some business-rule violations are deliberately planted and should be visible in ground_truth.csv/json."
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    (out/"validation_summary.json").write_text(json.dumps(checks,indent=2,default=str),encoding="utf-8")
    print(json.dumps(checks,indent=2,default=str)); con.close()
if __name__=="__main__": main()
