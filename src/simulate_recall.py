import argparse, sqlite3, csv, json
from pathlib import Path
from datetime import datetime

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",default="output/traceability.db")
    ap.add_argument("--out",default="output")
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(args.db); con.execute("PRAGMA foreign_keys=ON")
    recalls=con.execute("SELECT recall_id,trigger_lot_id,trigger_type FROM RecallCase").fetchall()
    metrics=[]
    for rec,trigger,typ in recalls:
        raw=set(); fins=set()
        if typ=="RAW":
            raw.add(trigger)
            orders=[r[0] for r in con.execute("SELECT DISTINCT production_order_id FROM MaterialConsumption WHERE material_lot_id=?",(trigger,))]
            for wo in orders:
                fins.update(r[0] for r in con.execute("SELECT finished_lot_id FROM FinishedLot WHERE production_order_id=?",(wo,)))
        else: fins.add(trigger)
        # downstream delivery/customer scope
        customers=set(); delivery_rows=[]
        for fid in fins:
            delivery_rows.extend(con.execute("SELECT delivery_id,customer_id,quantity_delivered FROM Delivery WHERE finished_lot_id=?",(fid,)).fetchall())
        customers={r[1] for r in delivery_rows}
        now=datetime.now().date().isoformat()
        # Scope records are append-only; ignore duplicates on rerun.
        for lot in raw:
            con.execute("INSERT OR IGNORE INTO RecallScope VALUES(?,?,?,?,?)",(f"RS-{rec}-{lot}",""+rec,lot,"RAW",now))
        for lot in fins:
            con.execute("INSERT OR IGNORE INTO RecallScope VALUES(?,?,?,?,?)",(f"RS-{rec}-{lot}",""+rec,lot,"FINISHED",now))
        # Notify every customer; record events. Quantity is the total delivered to that customer in scope.
       
        # Notify customers, with one deliberate omission for ANOM-003.
        # This creates a testable recall failure.
        deliberately_omitted_customer = (
            "CUST-00200"
            if rec == "REC-2026-000001" and "CUST-00200" in customers
            else None
        )

        notified = set(
            r[0] for r in con.execute(
                "SELECT target_id FROM RecallAction "
                "WHERE recall_id=? "
                "AND action_type='NOTIFY_CUSTOMER' "
                "AND action_status='COMPLETED'",
                (rec,)
            )
        )

        for cust in sorted(customers):
            if cust == deliberately_omitted_customer:
                continue

            if cust not in notified:
                qty = sum(
                    r[2] for r in delivery_rows if r[1] == cust
                )
                aid = f"ACT-{rec}-NOTIFY-{cust}"

                con.execute(
                    "INSERT OR IGNORE INTO RecallAction "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        aid, rec, "NOTIFY_CUSTOMER", "Customer",
                        cust, qty, "COMPLETED", now,
                        "Customer included by downstream genealogy traversal"
                    )
                )

        # Measure notification coverage against all affected customers.
        actual_notified = set(
            r[0] for r in con.execute(
                "SELECT target_id FROM RecallAction "
                "WHERE recall_id=? "
                "AND action_type='NOTIFY_CUSTOMER' "
                "AND action_status='COMPLETED'",
                (rec,)
            )
        )

        missing_customers = customers - actual_notified

        # Quarantine affected inventory and count it consistently on reruns.
        quarantined = 0

        for fid in fins:
            rows = con.execute(
                "SELECT inventory_id, quantity_on_hand, sale_status "
                "FROM Inventory WHERE finished_lot_id=?",
                (fid,)
            ).fetchall()

            for iid, qty, status in rows:
                if status == "AVAILABLE":
                    con.execute(
                        "UPDATE Inventory "
                        "SET sale_status='QUARANTINED', updated_at=? "
                        "WHERE inventory_id=?",
                        (now, iid)
                    )
                    status = "QUARANTINED"

                if status == "QUARANTINED":
                    quarantined += qty

                    aid = f"ACT-{rec}-QUAR-{iid}"
                    con.execute(
                        "INSERT OR IGNORE INTO RecallAction "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            aid, rec, "QUARANTINE", "Inventory",
                            iid, qty, "COMPLETED", now,
                            "Inventory blocked from sale"
                        )
                    )

            con.execute(
                "UPDATE FinishedLot SET status='RECALLED' "
                "WHERE finished_lot_id=?",
                (fid,)
            )
        # Recovery simulated as a proportion of delivered quantities, deterministic rule (not random labels).
        delivered=sum(r[2] for r in delivery_rows)
        recovered=int(delivered*0.65)
        if delivered:
            aid=f"ACT-{rec}-RECOVERY"
            con.execute("INSERT OR IGNORE INTO RecallAction VALUES(?,?,?,?,?,?,?,?,?)",(aid,rec,"RECOVER","RecallScope",rec,recovered,"COMPLETED",now,"Synthetic recovery assumption: 65% of delivered affected units"))
        total_actions=con.execute("SELECT COUNT(*) FROM RecallAction WHERE recall_id=?",(rec,)).fetchone()[0]
        metrics.append({"recall_id":rec,"trigger_lot_id":trigger,"trigger_type":typ,"affected_finished_lots":len(fins),"affected_customers":len(customers),"affected_deliveries":len(delivery_rows),"delivered_affected_units":delivered,"inventory_quarantined_units":quarantined,"recovered_units_simulated":recovered,"action_count":total_actions,"recovery_rate":round(recovered/delivered,4) if delivered else 0.0, "missing_notification_count": len(missing_customers),
"missing_notification_customer_ids": ";".join(sorted(missing_customers)),})
        con.execute("UPDATE RecallCase SET status='IN_PROGRESS' WHERE recall_id=?",(rec,))
    con.commit()
    with open(out/"recall_metrics.json","w",encoding="utf-8") as f: json.dump(metrics,f,indent=2)
    if metrics:
        with open(out/"recall_metrics.csv","w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(metrics[0])); w.writeheader(); w.writerows(metrics)
    print(json.dumps(metrics,indent=2))
    con.close()
if __name__=="__main__": main()
