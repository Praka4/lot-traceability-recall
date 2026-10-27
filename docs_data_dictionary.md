# Data Dictionary

All IDs are immutable strings. Dates use ISO-8601 `YYYY-MM-DD`. Quantities are non-negative numeric units unless an anomaly is explicitly labelled.

| Entity/table | Primary key | Fields and rules | Relationships |
|---|---|---|---|
| Supplier | supplier_id | supplier_name TEXT required; country TEXT required; risk_tier in LOW/MEDIUM/HIGH; active BOOLEAN | 1:N MaterialLot |
| MaterialLot | material_lot_id | supplier_id FK; material_code; quantity_received >= 0 units; received_date; expiry_date >= received_date; status in RELEASED/QUARANTINED/CONSUMED/EXPIRED; issue_type nullable | N:1 Supplier |
| Product | product_id | product_name; category; unit_weight_g > 0; active BOOLEAN | 1:N BOM, ProductionOrder, FinishedLot |
| BOM | bom_id | product_id FK; version; effective_from; effective_to nullable; status in ACTIVE/RETIRED; unique product/version | N:1 Product |
| BOMLine | bom_line_id | bom_id FK; material_code; qty_per_unit > 0; unit in g/ml/units; unique bom/material | N:1 BOM |
| ProductionOrder | production_order_id | product_id FK; bom_id FK; planned_quantity > 0; start_date; end_date >= start_date; status in PLANNED/RELEASED/COMPLETED/HOLD | N:1 Product/BOM |
| MaterialConsumption | consumption_id | production_order_id FK; material_lot_id FK; quantity_consumed > 0; consumed_at; unique order/lot | bridge: ProductionOrder N:M MaterialLot |
| FinishedLot | finished_lot_id | production_order_id FK; product_id FK; quantity_produced >= 0; produced_date; status in RELEASED/QUARANTINED/RECALLED; issue_type nullable | N:1 ProductionOrder |
| Customer | customer_id | customer_name; region; customer_type in RETAILER/DISTRIBUTOR/FOODSERVICE | 1:N Delivery |
| Shipment | shipment_id | warehouse_code; shipped_date; status in CREATED/SHIPPED/HELD/RECALLED | 1:N ShipmentLine |
| ShipmentLine | shipment_line_id | shipment_id FK; finished_lot_id FK; quantity_shipped > 0; unique shipment/lot | bridge: Shipment N:M FinishedLot |
| Delivery | delivery_id | shipment_id FK; customer_id FK; finished_lot_id FK; quantity_delivered > 0; delivered_date; status in DELIVERED/HELD/RETURNED; issue_type nullable | N:1 Shipment/Customer/FinishedLot |
| Inventory | inventory_id | finished_lot_id FK; warehouse_code; quantity_on_hand >= 0; sale_status in AVAILABLE/QUARANTINED/DEPLETED; updated_at | N:1 FinishedLot |
| RecallCase | recall_id | trigger_lot_id; trigger_type in RAW/FINISHED; reason; opened_at; severity in LOW/MEDIUM/HIGH/CRITICAL; status in OPEN/IN_PROGRESS/CLOSED | 1:N RecallAction; N:M lots via RecallScope |
| RecallScope | recall_scope_id | recall_id FK; affected_lot_id; affected_lot_type in RAW/FINISHED; discovered_at; unique recall/lot/type | bridge: RecallCase N:M affected lots |
| RecallAction | action_id | recall_id FK; action_type in NOTIFY_CUSTOMER/QUARANTINE/RECOVER/DISPOSE/INVESTIGATE; target_type; target_id; quantity_units >= 0; action_status in PENDING/COMPLETED/FAILED; event_time; notes | N:1 RecallCase; optional target refs |
| Ground truth | label_id | scenario_id; issue_type; entity_type; entity_id; expected_detection; expected_decision; rationale | Separate evaluation-only file/table export |

## Naming conventions
- `RAWLOT-<supplier-id>-2026-000001`
- `WO-2026-000001`
- `FINLOT-2026-000001`
- `SHP-2026-000001`
- `REC-2026-000001`

## Lifecycle rules
- A raw lot is RELEASED before consumption; quarantine blocks use.
- Production order transitions PLANNED -> RELEASED -> COMPLETED, or HOLD.
- Finished lots are RELEASED unless a recall or anomaly requires QUARANTINED/RECALLED.
- Shipments transition CREATED -> SHIPPED, or HELD/RECALLED.
- Recall actions are append-only events. A new event is added for each status change; historical events are never overwritten.
- Date order: received <= consumed <= production <= shipped <= delivered.
- Baseline quantity rules: total consumption per input lot cannot exceed received quantity; delivery quantity for a lot cannot exceed its produced quantity across all deliveries; normal shipment line totals should reconcile with associated deliveries.
- Exceptions deliberately violate selected rules and must be visible through `issue_type` and separate ground truth.
