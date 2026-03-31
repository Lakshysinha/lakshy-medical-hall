# Phase 2 — Data Model & System Design (Completed)

## Schema Coverage
The logical schema is implemented in the service layer and mirrored in SQL reference form in `docs/schema.sql`.

Tables covered:
- medicines
- batches
- stock_transactions
- short_list_view (derived)
- sales
- sale_items
- payment_transactions
- customer_records
- users
- audit_logs

## Key Constraints
- Unique batch number per medicine.
- EXP Date > MFG Date.
- Stock cannot be negative.
- Sold quantity cannot exceed available stock.
- Payment mode required for completed sale.

## Service/API Design
Implemented operations map to the following service contracts:
- `add_medicine`
- `add_batch`
- `search_medicine`
- `scan_code`
- `low_stock_short_list`
- `create_sale`
- `daily_summary`
- `customer_history`

## Security & Audit
- Role-based authorization checks in write operations.
- Audit log entries for batch creation and sales creation.
