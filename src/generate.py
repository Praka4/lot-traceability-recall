
import argparse
import csv
import json
import random
import sqlite3
from pathlib import Path
from datetime import date, timedelta


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE Supplier(
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    country TEXT NOT NULL,
    risk_tier TEXT NOT NULL CHECK(risk_tier IN ('LOW','MEDIUM','HIGH')),
    active INTEGER NOT NULL CHECK(active IN (0,1))
);

CREATE TABLE MaterialLot(
    material_lot_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES Supplier(supplier_id),
    material_code TEXT NOT NULL,
    quantity_received REAL NOT NULL CHECK(quantity_received>=0),
    received_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('RELEASED','QUARANTINED','CONSUMED','EXPIRED')),
    issue_type TEXT
);

CREATE TABLE Product(
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_weight_g REAL NOT NULL CHECK(unit_weight_g>0),
    active INTEGER NOT NULL CHECK(active IN (0,1))
);

CREATE TABLE BOM(
    bom_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    version INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RETIRED')),
    UNIQUE(product_id,version)
);

CREATE TABLE BOMLine(
    bom_line_id TEXT PRIMARY KEY,
    bom_id TEXT NOT NULL REFERENCES BOM(bom_id),
    material_code TEXT NOT NULL,
    qty_per_unit REAL NOT NULL CHECK(qty_per_unit>0),
    unit TEXT NOT NULL CHECK(unit IN ('g','ml','units')),
    UNIQUE(bom_id,material_code)
);

CREATE TABLE ProductionOrder(
    production_order_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    bom_id TEXT NOT NULL REFERENCES BOM(bom_id),
    planned_quantity INTEGER NOT NULL CHECK(planned_quantity>0),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PLANNED','RELEASED','COMPLETED','HOLD'))
);

CREATE TABLE MaterialConsumption(
    consumption_id TEXT PRIMARY KEY,
    production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id),
    material_lot_id TEXT NOT NULL REFERENCES MaterialLot(material_lot_id),
    quantity_consumed REAL NOT NULL CHECK(quantity_consumed>0),
    consumed_at TEXT NOT NULL,
    UNIQUE(production_order_id,material_lot_id)
);

CREATE TABLE FinishedLot(
    finished_lot_id TEXT PRIMARY KEY,
    production_order_id TEXT NOT NULL REFERENCES ProductionOrder(production_order_id),
    product_id TEXT NOT NULL REFERENCES Product(product_id),
    quantity_produced INTEGER NOT NULL CHECK(quantity_produced>=0),
    produced_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('RELEASED','QUARANTINED','RECALLED')),
    issue_type TEXT
);

CREATE TABLE Customer(
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region TEXT NOT NULL,
    customer_type TEXT NOT NULL CHECK(customer_type IN ('RETAILER','DISTRIBUTOR','FOODSERVICE'))
);

CREATE TABLE Shipment(
    shipment_id TEXT PRIMARY KEY,
    warehouse_code TEXT NOT NULL,
    shipped_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('CREATED','SHIPPED','HELD','RECALLED'))
);

CREATE TABLE ShipmentLine(
    shipment_line_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES Shipment(shipment_id),
    finished_lot_id TEXT NOT NULL REFERENCES FinishedLot(finished_lot_id),
    quantity_shipped INTEGER NOT NULL CHECK(quantity_shipped>0),
    UNIQUE(shipment_id,finished_lot_id)
);

CREATE TABLE Delivery(
    delivery_id TEXT PRIMARY KEY,
    shipment_id TEXT NOT NULL REFERENCES Shipment(shipment_id),
    customer_id TEXT NOT NULL REFERENCES Customer(customer_id),
    finished_lot_id TEXT NOT NULL REFERENCES FinishedLot(finished_lot_id),
    quantity_delivered INTEGER NOT NULL CHECK(quantity_delivered>0),
    delivered_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('DELIVERED','HELD','RETURNED')),
    issue_type TEXT
);

CREATE TABLE Inventory(
    inventory_id TEXT PRIMARY KEY,
    finished_lot_id TEXT NOT NULL REFERENCES FinishedLot(finished_lot_id),
    warehouse_code TEXT NOT NULL,
    quantity_on_hand INTEGER NOT NULL CHECK(quantity_on_hand>=0),
    sale_status TEXT NOT NULL CHECK(sale_status IN ('AVAILABLE','QUARANTINED','DEPLETED')),
    updated_at TEXT NOT NULL
);

CREATE TABLE RecallCase(
    recall_id TEXT PRIMARY KEY,
    trigger_lot_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL CHECK(trigger_type IN ('RAW','FINISHED')),
    reason TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    status TEXT NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','CLOSED'))
);

CREATE TABLE RecallScope(
    recall_scope_id TEXT PRIMARY KEY,
    recall_id TEXT NOT NULL REFERENCES RecallCase(recall_id),
    affected_lot_id TEXT NOT NULL,
    affected_lot_type TEXT NOT NULL CHECK(affected_lot_type IN ('RAW','FINISHED')),
    discovered_at TEXT NOT NULL,
    UNIQUE(recall_id,affected_lot_id,affected_lot_type)
);

CREATE TABLE RecallAction(
    action_id TEXT PRIMARY KEY,
    recall_id TEXT NOT NULL REFERENCES RecallCase(recall_id),
    action_type TEXT NOT NULL CHECK(action_type IN ('NOTIFY_CUSTOMER','QUARANTINE','RECOVER','DISPOSE','INVESTIGATE')),
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    quantity_units REAL NOT NULL CHECK(quantity_units>=0),
    action_status TEXT NOT NULL CHECK(action_status IN ('PENDING','COMPLETED','FAILED')),
    event_time TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE GenealogyException(
    exception_id TEXT PRIMARY KEY,
    finished_lot_id TEXT NOT NULL REFERENCES FinishedLot(finished_lot_id),
    missing_material_lot_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE GroundTruth(
    label_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    expected_detection TEXT NOT NULL,
    expected_decision TEXT NOT NULL,
    rationale TEXT NOT NULL
);
"""


def d(days):
    """Convert an offset from 2026-01-01 into an ISO date."""
    return (date(2026, 1, 1) + timedelta(days=int(days))).isoformat()


def export_table(conn, table, out):
    """Export a database table to CSV and JSON."""
    cur = conn.execute(f'SELECT * FROM "{table}"')
    columns = [item[0] for item in cur.description]
    rows = cur.fetchall()

    csv_path = out / "csv" / f"{table.lower()}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)

    json_path = out / "json" / f"{table.lower()}.json"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(
            [dict(zip(columns, row)) for row in rows],
            file,
            indent=2
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generate a synthetic lot traceability and recall database."
    )
    parser.add_argument("--out", default="output")
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )
    args = parser.parse_args()

    out = Path(args.out)
    (out / "csv").mkdir(parents=True, exist_ok=True)
    (out / "json").mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)

    if args.scale == "full":
        n_sup, n_raw, n_wo, n_fin, n_del = 500, 10000, 5000, 8000, 20000
    else:
        n_sup, n_raw, n_wo, n_fin, n_del = 25, 250, 125, 200, 500

    db_path = out / "traceability.db"

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    # ---------------------------------------------------------
    # 1. Suppliers
    # ---------------------------------------------------------
    suppliers = []

    for i in range(1, n_sup + 1):
        supplier_id = f"SUP-{i:05d}"
        suppliers.append(supplier_id)

        conn.execute(
            "INSERT INTO Supplier VALUES(?,?,?,?,?)",
            (
                supplier_id,
                f"Supplier {i:05d}",
                rng.choice(["IN", "US", "DE", "SG", "GB"]),
                rng.choices(
                    ["LOW", "MEDIUM", "HIGH"],
                    weights=[0.65, 0.27, 0.08]
                )[0],
                1
            )
        )

    # ---------------------------------------------------------
    # 2. Products, bills of materials, and BOM lines
    # ---------------------------------------------------------
    products = []

    for i in range(1, 11):
        product_id = f"PROD-{i:03d}"
        bom_id = f"BOM-{i:03d}-V01"
        products.append(product_id)

        conn.execute(
            "INSERT INTO Product VALUES(?,?,?,?,?)",
            (
                product_id,
                f"Product {i:03d}",
                rng.choice(["FOOD", "BEVERAGE", "CONSUMER"]),
                round(rng.uniform(80, 750), 2),
                1
            )
        )

        conn.execute(
            "INSERT INTO BOM VALUES(?,?,?,?,?,?)",
            (bom_id, product_id, 1, "2026-01-01", None, "ACTIVE")
        )

        for j, material_code in enumerate(
            ["MAT-A", "MAT-B", "MAT-C"], start=1
        ):
            conn.execute(
                "INSERT INTO BOMLine VALUES(?,?,?,?,?)",
                (
                    f"BOMLINE-{i:03d}-{j}",
                    bom_id,
                    material_code,
                    round(rng.uniform(0.01, 0.08), 4),
                    "g"
                )
            )

    # ---------------------------------------------------------
    # 3. Customers
    # ---------------------------------------------------------
    customers = []

    for i in range(1, 301):
        customer_id = f"CUST-{i:05d}"
        customers.append(customer_id)

        conn.execute(
            "INSERT INTO Customer VALUES(?,?,?,?)",
            (
                customer_id,
                f"Customer {i:05d}",
                rng.choice(["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]),
                rng.choice(["RETAILER", "DISTRIBUTOR", "FOODSERVICE"])
            )
        )

    # ---------------------------------------------------------
    # 4. Raw material lots
    # ---------------------------------------------------------
    raw_ids = []
    raw_by_mat = {
        "MAT-A": [],
        "MAT-B": [],
        "MAT-C": []
    }

    contaminated_count = max(1, n_raw // 100)
    contaminated = set(
        rng.sample(range(n_raw), contaminated_count)
    )

    for i in range(n_raw):
        supplier_id = rng.choice(suppliers)
        raw_id = f"RAWLOT-{supplier_id}-2026-{i + 1:06d}"
        raw_ids.append(raw_id)

        received_day = rng.randrange(0, 240)
        expiry_day = max(received_day, rng.randrange(250, 365))

        received_date = d(received_day)
        expiry_date = d(expiry_day)

        material_code = rng.choice(["MAT-A", "MAT-B", "MAT-C"])

        # Contamination is hidden from the operational table later.
        issue_type = "CONTAMINATED" if i in contaminated else None

        raw_by_mat[material_code].append(raw_id)

        conn.execute(
            "INSERT INTO MaterialLot VALUES(?,?,?,?,?,?,?,?)",
            (
                raw_id,
                supplier_id,
                material_code,
                rng.randint(800, 8000),
                received_date,
                expiry_date,
                "RELEASED",
                issue_type
            )
        )

    # ---------------------------------------------------------
    # 5. Production orders, material consumption, finished lots
    # ---------------------------------------------------------
    fin_ids = []

    # Every production order gets at least one finished lot.
    # Additional finished lots bring the total to n_fin.
    n_fin_by_order = [1] * n_wo

    for k in range(n_fin - n_wo):
        n_fin_by_order[k % n_wo] += 1

    for i in range(n_wo):
        product_id = rng.choice(products)
        product_number = int(product_id[-3:])
        bom_id = f"BOM-{product_number:03d}-V01"

        start_day = rng.randrange(30, 270)
        end_day = max(start_day, rng.randrange(30, 300))

        start_date = d(start_day)
        end_date = d(end_day)

        order_id = f"WO-2026-{i + 1:06d}"
        planned_quantity = rng.randint(300, 1800)

        conn.execute(
            "INSERT INTO ProductionOrder VALUES(?,?,?,?,?,?,?)",
            (
                order_id,
                product_id,
                bom_id,
                planned_quantity,
                start_date,
                end_date,
                "COMPLETED"
            )
        )

        material_rows = conn.execute(
            "SELECT material_code FROM BOMLine WHERE bom_id = ?",
            (bom_id,)
        ).fetchall()

        for j, (material_code,) in enumerate(material_rows, start=1):
            candidate_lots = raw_by_mat[material_code]
            raw_id = rng.choice(candidate_lots)
            quantity_consumed = round(
                planned_quantity * rng.uniform(0.01, 0.08),
                2
            )

            conn.execute(
                "INSERT INTO MaterialConsumption VALUES(?,?,?,?,?)",
                (
                    f"CONS-{i + 1:06d}-{j}",
                    order_id,
                    raw_id,
                    quantity_consumed,
                    end_date
                )
            )

        lots_for_order = n_fin_by_order[i]
        quantity_per_lot = max(1, planned_quantity // lots_for_order)

        for _ in range(lots_for_order):
            finished_number = len(fin_ids) + 1
            finished_id = f"FINLOT-2026-{finished_number:06d}"
            fin_ids.append(finished_id)

            conn.execute(
                "INSERT INTO FinishedLot VALUES(?,?,?,?,?,?,?)",
                (
                    finished_id,
                    order_id,
                    product_id,
                    quantity_per_lot,
                    end_date,
                    "RELEASED",
                    None
                )
            )

    # ---------------------------------------------------------
    # 6. Shipments
    # ---------------------------------------------------------
    shipment_count = max(1, n_del // 3)

    for i in range(shipment_count):
        shipment_id = f"SHP-2026-{i + 1:06d}"
        ship_date = d(rng.randrange(80, 350))

        conn.execute(
            "INSERT INTO Shipment VALUES(?,?,?,?)",
            (
                shipment_id,
                f"WH-{rng.randint(1, 8):02d}",
                ship_date,
                "SHIPPED"
            )
        )

    shipment_dates = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT shipment_id, shipped_date FROM Shipment"
        )
    }

    finished_dates = {
        row[0]: (row[1], row[2])
        for row in conn.execute(
            "SELECT finished_lot_id, quantity_produced, produced_date "
            "FROM FinishedLot"
        )
    }

    # Track remaining units so normal deliveries never exceed production.
    remaining_by_fin = {
        finished_id: finished_dates[finished_id][0]
        for finished_id in fin_ids
    }

    eligible_fin = list(fin_ids)

    # ---------------------------------------------------------
    # 7. Deliveries and shipment lines
    # ---------------------------------------------------------
    for i in range(n_del):
        if not eligible_fin:
            raise RuntimeError(
                "No finished inventory remains, so the requested number "
                "of deliveries cannot be generated."
            )

        delivery_id = f"DEL-{i + 1:07d}"
        shipment_id = f"SHP-2026-{(i % shipment_count) + 1:06d}"

        # Select only a finished lot that still has stock available.
        finished_id = rng.choice(eligible_fin)
        customer_id = rng.choice(customers)

        remaining = remaining_by_fin[finished_id]
        quantity_delivered = rng.randint(1, min(100, remaining))

        remaining_by_fin[finished_id] -= quantity_delivered

        if remaining_by_fin[finished_id] == 0:
            eligible_fin.remove(finished_id)

        produced_date = finished_dates[finished_id][1]
        ship_date = shipment_dates[shipment_id]
        delivered_date = max(ship_date, produced_date)

        conn.execute(
            "INSERT INTO Delivery VALUES(?,?,?,?,?,?,?,?)",
            (
                delivery_id,
                shipment_id,
                customer_id,
                finished_id,
                quantity_delivered,
                delivered_date,
                "DELIVERED",
                None
            )
        )

        # Keep ShipmentLine quantities reconciled with normal deliveries.
        existing_line = conn.execute(
            """
            SELECT 1
            FROM ShipmentLine
            WHERE shipment_id = ? AND finished_lot_id = ?
            """,
            (shipment_id, finished_id)
        ).fetchone()

        if existing_line:
            conn.execute(
                """
                UPDATE ShipmentLine
                SET quantity_shipped = quantity_shipped + ?
                WHERE shipment_id = ? AND finished_lot_id = ?
                """,
                (quantity_delivered, shipment_id, finished_id)
            )
        else:
            conn.execute(
                "INSERT INTO ShipmentLine VALUES(?,?,?,?)",
                (
                    f"SL-{shipment_id}-{finished_id}",
                    shipment_id,
                    finished_id,
                    quantity_delivered
                )
            )

    # ---------------------------------------------------------
    # 8. Inventory
    # ---------------------------------------------------------
    for index, finished_id in enumerate(fin_ids, start=1):
        produced_quantity = finished_dates[finished_id][0]
        delivered_quantity = conn.execute(
            """
            SELECT COALESCE(SUM(quantity_delivered), 0)
            FROM Delivery
            WHERE finished_lot_id = ?
            """,
            (finished_id,)
        ).fetchone()[0]

        on_hand = max(0, produced_quantity - delivered_quantity)

        conn.execute(
            "INSERT INTO Inventory VALUES(?,?,?,?,?,?)",
            (
                f"INV-{index:07d}",
                finished_id,
                f"WH-{rng.randint(1, 8):02d}",
                on_hand,
                "AVAILABLE" if on_hand else "DEPLETED",
                "2026-10-01"
            )
        )

    # ---------------------------------------------------------
    # 9. Ground-truth labels and deliberately planted anomalies
    # ---------------------------------------------------------
    truth = []

    def label(
        scenario,
        issue,
        entity_type,
        entity_id,
        detection,
        decision,
        rationale
    ):
        label_id = f"GT-{len(truth) + 1:04d}"

        record = (
            label_id,
            scenario,
            issue,
            entity_type,
            entity_id,
            detection,
            decision,
            rationale
        )

        truth.append(record)

        conn.execute(
            "INSERT INTO GroundTruth VALUES(?,?,?,?,?,?,?,?)",
            record
        )

    # Anomaly 1: genealogy gap without breaking foreign-key integrity.
    if fin_ids:
        first_finished_id = fin_ids[0]

        label(
            "ANOM-001",
            "MISSING_INPUT_LOT",
            "FinishedLot",
            first_finished_id,
            "YES",
            "FLAG_GENEALOGY_GAP",
            "Simulated genealogy gap; the missing source is recorded "
            "in GenealogyException without violating core foreign keys."
        )

        conn.execute(
            "UPDATE FinishedLot SET issue_type = ? "
            "WHERE finished_lot_id = ?",
            ("MISSING_INPUT_LOT", first_finished_id)
        )

        conn.execute(
            "INSERT INTO GenealogyException VALUES(?,?,?,?,?)",
            (
                "GEX-000001",
                first_finished_id,
                "RAWLOT-MISSING-2026-999999",
                "MISSING_INPUT_LOT",
                "2026-10-01"
            )
        )

    # Anomaly 2: deliberately inflate one delivery.
    first_delivery = conn.execute(
        """
        SELECT delivery_id, finished_lot_id
        FROM Delivery
        ORDER BY delivery_id
        LIMIT 1
        """
    ).fetchone()

    if first_delivery:
        delivery_id, finished_id = first_delivery

        produced_quantity = conn.execute(
            "SELECT quantity_produced FROM FinishedLot "
            "WHERE finished_lot_id = ?",
            (finished_id,)
        ).fetchone()[0]

        # This intentionally creates one overdelivery anomaly.
        conn.execute(
            """
            UPDATE Delivery
            SET quantity_delivered = ?,
                issue_type = ?
            WHERE delivery_id = ?
            """,
            (
                produced_quantity + 1000,
                "DELIVERED_EXCEEDS_PRODUCED",
                delivery_id
            )
        )

        label(
            "ANOM-002",
            "DELIVERED_EXCEEDS_PRODUCED",
            "Delivery",
            delivery_id,
            "YES",
            "BLOCK_AND_INVESTIGATE",
            "Deliberately inflated delivery quantity for anomaly detection."
        )

        # Choose a used raw lot that reaches at least three customers.
    trigger_lot = None

    for raw_id in raw_ids:
        downstream_customers = {
            row[0] for row in conn.execute(
                """
                SELECT DISTINCT d.customer_id
                FROM MaterialConsumption mc
                JOIN FinishedLot fl
                  ON fl.production_order_id = mc.production_order_id
                JOIN Delivery d
                  ON d.finished_lot_id = fl.finished_lot_id
                WHERE mc.material_lot_id = ?
                """,
                (raw_id,)
            ).fetchall()
        }

        if len(downstream_customers) == 3:
            trigger_lot = raw_id
            break

    # Anomaly 3: recall with a deliberately omitted customer notification.
    if trigger_lot:
        # Keep the synthetic test scenario deterministic: exactly three
        # downstream customers, including the customer whose notice is omitted.
        affected_delivery_ids = [
            row[0] for row in conn.execute(
                """
                SELECT d.delivery_id
                FROM MaterialConsumption mc
                JOIN FinishedLot fl
                  ON fl.production_order_id = mc.production_order_id
                JOIN Delivery d
                  ON d.finished_lot_id = fl.finished_lot_id
                WHERE mc.material_lot_id = ?
                ORDER BY d.delivery_id
                """,
                (trigger_lot,)
            ).fetchall()
        ]

        test_customers = [
            "CUST-00200",
            "CUST-00201",
            "CUST-00202",
        ]

        for index, delivery_id in enumerate(affected_delivery_ids):
            conn.execute(
                "UPDATE Delivery SET customer_id = ? WHERE delivery_id = ?",
                (test_customers[index % 3], delivery_id)
            )

        recall_id = "REC-2026-000001"

        conn.execute(
            "INSERT INTO RecallCase VALUES(?,?,?,?,?,?,?)",
            (
                recall_id,
                trigger_lot,
                "RAW",
                "Suspected contaminated input material",
                "2026-10-01",
                "CRITICAL",
                "OPEN"
            )
        )

        label(
            "ANOM-003",
            "RECALL_MISSES_DOWNSTREAM_CUSTOMER",
            "RecallCase",
            recall_id,
            "YES",
            "NOTIFY_ALL_DOWNSTREAM_CUSTOMERS",
            "The recall simulator should detect and report omitted "
            "customer notifications."
        )

    # Anomaly 4: downstream recalled inventory remains available.
    recalled_finished_lots = []

    if trigger_lot:
        recalled_finished_lots = [
            row[0]
            for row in conn.execute(
                """
                SELECT DISTINCT f.finished_lot_id
                FROM FinishedLot f
                JOIN MaterialConsumption c
                  ON c.production_order_id = f.production_order_id
                WHERE c.material_lot_id = ?
                ORDER BY f.finished_lot_id
                """,
                (trigger_lot,)
            ).fetchall()
        ]

    if recalled_finished_lots:
        recalled_finished_id = recalled_finished_lots[0]

        inventory = conn.execute(
            """
            SELECT inventory_id
            FROM Inventory
            WHERE finished_lot_id = ?
            ORDER BY inventory_id
            LIMIT 1
            """,
            (recalled_finished_id,)
        ).fetchone()

        if inventory:
            conn.execute(
                "UPDATE Inventory SET sale_status = 'AVAILABLE' "
                "WHERE inventory_id = ?",
                (inventory[0],)
            )

            label(
                "ANOM-004",
                "RECALLED_INVENTORY_AVAILABLE",
                "Inventory",
                inventory[0],
                "YES",
                "QUARANTINE_IMMEDIATELY",
                "Inventory downstream of the contaminated raw lot "
                "is deliberately left available for testing."
            )

    # Hide contamination indicators in operational data.
    # GroundTruth retains the expected evaluation labels.
    for index in sorted(contaminated):
        raw_id = raw_ids[index]

        conn.execute(
            "UPDATE MaterialLot SET issue_type = NULL "
            "WHERE material_lot_id = ?",
            (raw_id,)
        )

        label(
            f"CONTAM-{index + 1:06d}",
            "CONTAMINATED_SOURCE_LOT",
            "MaterialLot",
            raw_id,
            "YES",
            "OPEN_RECALL_IF_USED",
            "Synthetic hidden label for contamination evaluation."
        )

    # ---------------------------------------------------------
    # 10. Commit and export
    # ---------------------------------------------------------
    conn.commit()

    tables = [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        if row[0] != "GroundTruth"
    ]

    for table in tables:
        export_table(conn, table, out)

    ground_truth_rows = conn.execute(
        "SELECT * FROM GroundTruth ORDER BY label_id"
    ).fetchall()

    columns = [
        item[0]
        for item in conn.execute(
            "SELECT * FROM GroundTruth LIMIT 0"
        ).description
    ]

    with open(
        out / "ground_truth.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(ground_truth_rows)

    with open(
        out / "ground_truth.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            [
                dict(zip(columns, row))
                for row in ground_truth_rows
            ],
            file,
            indent=2
        )

    with open(out / "schema.sql", "w", encoding="utf-8") as file:
        file.write(SCHEMA)

    counts = {
        table: conn.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
        for table in tables
    }

    counts["GroundTruth"] = len(ground_truth_rows)

    foreign_key_violations = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    manifest = {
        "seed": args.seed,
        "scale": args.scale,
        "counts": counts,
        "database": "traceability.db",
        "synthetic_only": True
    }

    (out / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    validation_summary = {
        "generation": "completed",
        "foreign_key_check": foreign_key_violations,
        "pass_fk_integrity": len(foreign_key_violations) == 0,
        "table_counts": counts
    }

    (out / "validation_summary.json").write_text(
        json.dumps(validation_summary, indent=2),
        encoding="utf-8"
    )

    conn.close()

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
