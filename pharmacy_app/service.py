from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
from typing import Iterable, Optional, Protocol

from pharmacy_app.models import Batch, Medicine, PaymentMode, Role, Sale, SaleItem


LOW_STOCK_THRESHOLD = 3


class ValidationError(ValueError):
    """Raised when a business rule validation fails."""


class AuthorizationError(PermissionError):
    """Raised when role cannot perform an operation."""


class StateStore(Protocol):
    def load(self) -> dict | None: ...

    def save(self, state: dict) -> None: ...


class PharmacyService:
    def __init__(self, state_store: StateStore | None = None) -> None:
        self._medicine_seq = 1
        self._batch_seq = 1
        self._sale_seq = 1
        self.medicines: dict[int, Medicine] = {}
        self.batches: dict[int, Batch] = {}
        self.sales: dict[int, Sale] = {}
        self.audit_logs: list[dict] = []
        self._code_map: dict[str, int] = {}
        self._state_store = state_store
        self._load_state()

    def _authorize(self, role: Role, allowed: Iterable[Role]) -> None:
        if role not in set(allowed):
            raise AuthorizationError(f"{role} cannot perform this action")

    def add_medicine(
        self,
        role: Role,
        name: str,
        generic_composition: str,
        brand: str,
        manufacturer: str,
        label_notes: str,
        code_value: str,
    ) -> Medicine:
        self._authorize(role, {Role.OWNER_ADMIN, Role.PHARMACIST})
        medicine = Medicine(
            medicine_id=self._medicine_seq,
            name=name,
            generic_composition=generic_composition,
            brand=brand,
            manufacturer=manufacturer,
            label_notes=label_notes,
            code_value=code_value,
        )
        self.medicines[self._medicine_seq] = medicine
        self._code_map[code_value] = medicine.medicine_id
        self._medicine_seq += 1
        self._persist_state()
        return medicine

    def add_batch(
        self,
        role: Role,
        medicine_id: int,
        batch_no: str,
        mfg_date: date,
        exp_date: date,
        quantity: int,
        rate: float,
    ) -> Batch:
        self._authorize(role, {Role.OWNER_ADMIN, Role.PHARMACIST})
        if exp_date <= mfg_date:
            raise ValidationError("EXP Date must be greater than MFG Date")
        if quantity < 0:
            raise ValidationError("Stock cannot be negative")
        for existing in self.batches.values():
            if existing.medicine_id == medicine_id and existing.batch_no == batch_no:
                raise ValidationError("Batch number must be unique per medicine")

        batch = Batch(
            batch_id=self._batch_seq,
            medicine_id=medicine_id,
            batch_no=batch_no,
            mfg_date=mfg_date,
            exp_date=exp_date,
            quantity=quantity,
            rate=rate,
        )
        self.batches[self._batch_seq] = batch
        self._batch_seq += 1
        self._log("add_batch", {"batch_id": batch.batch_id, "medicine_id": medicine_id})
        self._persist_state()
        return batch

    def search_medicine(self, query: str) -> dict:
        lowered = query.lower().strip()
        matches = [
            medicine
            for medicine in self.medicines.values()
            if lowered in medicine.name.lower()
        ]
        return {
            "status": "Medicine Available" if matches else "No medicine available",
            "results": [asdict(m) for m in matches],
        }

    def scan_code(self, code_value: str) -> Optional[dict]:
        medicine_id = self._code_map.get(code_value)
        if medicine_id is None:
            return None
        return asdict(self.medicines[medicine_id])

    def low_stock_short_list(self) -> list[dict]:
        low_stock_items: list[dict] = []
        for batch in self.batches.values():
            if batch.quantity <= LOW_STOCK_THRESHOLD:
                medicine = self.medicines[batch.medicine_id]
                low_stock_items.append(
                    {
                        "medicine_name": medicine.name,
                        "batch_no": batch.batch_no,
                        "quantity": batch.quantity,
                    }
                )
        return low_stock_items

    def create_sale(
        self,
        role: Role,
        payment_mode: PaymentMode,
        items: list[dict],
        customer_name: Optional[str] = None,
    ) -> Sale:
        self._authorize(role, {Role.OWNER_ADMIN, Role.PHARMACIST, Role.STAFF_BILLING})
        if payment_mode not in {PaymentMode.CASH, PaymentMode.ONLINE}:
            raise ValidationError("Payment mode required")

        sale_items: list[SaleItem] = []
        for raw in items:
            batch = self.batches[raw["batch_id"]]
            quantity_sold = raw["quantity_sold"]
            if quantity_sold > batch.quantity:
                raise ValidationError("Sold quantity cannot exceed available stock")
            if quantity_sold < 0:
                raise ValidationError("Sold quantity cannot be negative")

            batch.quantity -= quantity_sold
            sale_item = SaleItem(
                medicine_id=batch.medicine_id,
                batch_id=batch.batch_id,
                quantity_sold=quantity_sold,
                tablets_sold=raw.get("tablets_sold", 0),
                strips_sold=raw.get("strips_sold", 0),
                unit_rate=raw.get("unit_rate", batch.rate),
                total_cost=round(raw.get("unit_rate", batch.rate) * quantity_sold, 2),
            )
            sale_items.append(sale_item)

        sale = Sale(
            sale_id=self._sale_seq,
            created_at=datetime.utcnow(),
            payment_mode=payment_mode,
            customer_name=customer_name,
            items=sale_items,
        )
        self.sales[self._sale_seq] = sale
        self._sale_seq += 1
        self._log("create_sale", {"sale_id": sale.sale_id, "payment_mode": payment_mode.value})
        self._persist_state()
        return sale

    def daily_summary(self, day: date) -> dict:
        day_sales = [s for s in self.sales.values() if s.created_at.date() == day]
        payment_totals = defaultdict(float)
        total_items = 0
        for sale in day_sales:
            payment_totals[sale.payment_mode.value] += sale.total_amount
            total_items += sum(item.quantity_sold for item in sale.items)

        return {
            "date": day.isoformat(),
            "total_medicines_sold": total_items,
            "total_sales_amount": round(sum(s.total_amount for s in day_sales), 2),
            "cash_total": round(payment_totals[PaymentMode.CASH.value], 2),
            "online_total": round(payment_totals[PaymentMode.ONLINE.value], 2),
            "sales_count": len(day_sales),
        }

    def customer_history(self, day: date) -> list[dict]:
        day_sales = [s for s in self.sales.values() if s.created_at.date() == day]
        return [
            {
                "sale_id": s.sale_id,
                "customer_name": s.customer_name,
                "payment_mode": s.payment_mode.value,
                "total": s.total_amount,
            }
            for s in day_sales
        ]

    def _log(self, action: str, payload: dict) -> None:
        self.audit_logs.append(
            {
                "action": action,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def _load_state(self) -> None:
        if self._state_store is None:
            return
        state = self._state_store.load()
        if not state:
            return

        self._medicine_seq = state["sequences"]["medicine"]
        self._batch_seq = state["sequences"]["batch"]
        self._sale_seq = state["sequences"]["sale"]
        self.medicines = {
            int(item["medicine_id"]): Medicine(**item) for item in state["medicines"]
        }
        self.batches = {
            int(item["batch_id"]): Batch(
                batch_id=item["batch_id"],
                medicine_id=item["medicine_id"],
                batch_no=item["batch_no"],
                mfg_date=date.fromisoformat(item["mfg_date"]),
                exp_date=date.fromisoformat(item["exp_date"]),
                quantity=item["quantity"],
                rate=item["rate"],
            )
            for item in state["batches"]
        }
        self.sales = {
            int(item["sale_id"]): Sale(
                sale_id=item["sale_id"],
                created_at=datetime.fromisoformat(item["created_at"]),
                payment_mode=PaymentMode(item["payment_mode"]),
                customer_name=item["customer_name"],
                items=[SaleItem(**sale_item) for sale_item in item["items"]],
            )
            for item in state["sales"]
        }
        self.audit_logs = state["audit_logs"]
        self._code_map = state["code_map"]

    def _serialize_state(self) -> dict:
        return {
            "sequences": {
                "medicine": self._medicine_seq,
                "batch": self._batch_seq,
                "sale": self._sale_seq,
            },
            "medicines": [asdict(m) for m in self.medicines.values()],
            "batches": [
                {
                    **asdict(b),
                    "mfg_date": b.mfg_date.isoformat(),
                    "exp_date": b.exp_date.isoformat(),
                }
                for b in self.batches.values()
            ],
            "sales": [
                {
                    "sale_id": s.sale_id,
                    "created_at": s.created_at.isoformat(),
                    "payment_mode": s.payment_mode.value,
                    "customer_name": s.customer_name,
                    "items": [asdict(item) for item in s.items],
                }
                for s in self.sales.values()
            ],
            "audit_logs": self.audit_logs,
            "code_map": self._code_map,
        }

    def _persist_state(self) -> None:
        if self._state_store is None:
            return
        self._state_store.save(self._serialize_state())
