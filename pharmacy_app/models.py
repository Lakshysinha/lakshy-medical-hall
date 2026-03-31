from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Role(str, Enum):
    OWNER_ADMIN = "owner_admin"
    PHARMACIST = "pharmacist"
    STAFF_BILLING = "staff_billing"


class PaymentMode(str, Enum):
    CASH = "cash"
    ONLINE = "online"


@dataclass(slots=True)
class Medicine:
    medicine_id: int
    name: str
    generic_composition: str
    brand: str
    manufacturer: str
    label_notes: str
    code_value: str


@dataclass(slots=True)
class Batch:
    batch_id: int
    medicine_id: int
    batch_no: str
    mfg_date: date
    exp_date: date
    quantity: int
    rate: float


@dataclass(slots=True)
class SaleItem:
    medicine_id: int
    batch_id: int
    quantity_sold: int
    tablets_sold: int
    strips_sold: int
    unit_rate: float
    total_cost: float


@dataclass(slots=True)
class Sale:
    sale_id: int
    created_at: datetime
    payment_mode: PaymentMode
    customer_name: Optional[str]
    items: list[SaleItem] = field(default_factory=list)

    @property
    def total_amount(self) -> float:
        return round(sum(item.total_cost for item in self.items), 2)
