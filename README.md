# Lot Traceability \& Product Recall Simulator

A reproducible synthetic supply-chain dataset and recall simulation built with Python and SQLite.

## Features

* Deterministic synthetic master and transaction data.
* Suppliers, material lots, products, BOMs, production orders, input consumption, finished lots, customers, shipments, deliveries, inventory, recall cases and recall actions.
* Forward genealogy from contaminated raw lots to finished lots, shipments and customers.
* Recall actions for notification, quarantine, recovery and disposition.
* Four labelled exception scenarios: missing input lot, delivery over production, missed downstream customer, and recalled inventory still available for sale.
* Ground truth kept separate from operational input data.
* CSV/JSON exports, SQL database, validation summary and reproducibility checks.

## Requirements

* Python 3.10+
* No third-party packages required for generation, validation or simulation.
* `pytest` is optional for running the tests.

## Quick start

From this directory:

```bash
python src/generate.py --out output --seed 20261022 --scale starter
python src/validate.py --db output/traceability.db --out output
python src/simulate\_recall.py --db output/traceability.db --out output
python src/reproducibility.py --seed 20261022 --scale starter
```

For full requested volume:

```bash
python src/generate.py --out output\_full --seed 20261022 --scale full
python src/validate.py --db output\_full/traceability.db --out output\_full
python src/simulate\_recall.py --db output\_full/traceability.db --out output\_full
```

`starter` creates a smaller dataset for fast local development. `full` uses 500 suppliers, 10,000 raw lots, 5,000 production orders, 8,000 finished lots and 20,000 deliveries. The same seed and rules are used at both scales.

## Important data separation

* Operational tables are stored in `traceability.db` and exported under `output/csv` and `output/json`.
* `ground\_truth.csv` and `ground\_truth.json` contain planted anomaly labels and are kept separate from operational inputs.
* Do not use ground-truth fields as model input features when evaluating anomaly detection.

## Domain assumptions

* Quantities are in units unless a field explicitly says otherwise.
* Each finished lot has one production order. A production order may consume multiple material lots.
* The BOM defines the material requirements for a product. Consumption is stored in a bridge table.
* A shipment may contain multiple finished lots, and a finished lot may be split across multiple shipments.
* A delivery links a shipment to a customer and finished lot.
* Recall scope is computed by graph traversal from a trigger lot; it is not randomly assigned.
* The generator deliberately creates a small number of labelled anomalies after generating a valid baseline. Some anomaly rows intentionally violate normal rules and are identified in ground truth.
* Effective dates are stored where applicable. Event records are append-only; action history is not overwritten.

## Entity/cardinality overview

* Supplier 1:N MaterialLot
* Product 1:N BOM versions; Product 1:N ProductionOrder
* ProductionOrder N:M MaterialLot through MaterialConsumption
* ProductionOrder 1:N FinishedLot (the generated baseline uses one finished lot per order where possible)
* FinishedLot N:M Shipment through ShipmentLine
* Shipment 1:N Delivery
* Customer 1:N Delivery
* RecallCase 1:N RecallAction
* RecallCase N:M affected lots through RecallScope
* RecallAction optionally references a lot, customer, shipment or delivery

## Data dictionary

See `docs/data\_dictionary.md` for field types, requiredness, allowed values, units, uniqueness and validation rules.

## Acceptance checks

1. Primary keys are unique.
2. Foreign keys are enabled and checked.
3. Normal rows reconcile across production and distribution.
4. All planted exceptions are labelled in ground truth.
5. Recall genealogy is computed from source records.
6. Notification/quarantine/recovery actions are persisted as events.
7. Fixed-seed generation is repeatable.

## Lawful provenance

All records are synthetic. No personal or confidential data is used. The schema is inspired by common supply-chain traceability concepts; no external dataset is redistributed.

