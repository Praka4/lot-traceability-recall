# Architecture and Business Rules

## Processing pipeline
1. Generate master data (Supplier, Product, BOM, Customer).
2. Generate material lots and production orders.
3. Generate consumption bridge records and finished lots.
4. Generate shipments, shipment lines, deliveries and inventory.
5. Add labelled exceptions and hidden contamination ground truth.
6. Validate relational integrity and business reconciliations.
7. Traverse genealogy for each recall trigger.
8. Persist recall scope and action events.
9. Calculate metrics from the source tables.

## Core recall traversal
For a raw trigger:
`MaterialLot -> MaterialConsumption -> ProductionOrder -> FinishedLot -> Delivery -> Customer`
and also:
`FinishedLot -> Inventory` for quarantine.

For a finished trigger:
`FinishedLot -> Delivery -> Customer`, plus inventory rows.

## Metrics
- affected finished lots
- affected customers
- affected deliveries
- delivered affected units
- inventory units quarantined
- recovered units (simulated as a documented 65% assumption)
- recovery rate = recovered units / delivered affected units
- action count
- FK integrity and duplicate-key checks

## Exception policy
An anomaly is not silently mixed into the baseline. Use `issue_type` where possible and always record scenario labels in the separate ground-truth file. The missing-input-lot scenario is represented in GenealogyException: the finished lot is a valid FK, while the missing material-lot ID is intentionally stored as a non-FK exception reference. This preserves core relational integrity while making the genealogy gap directly testable.
