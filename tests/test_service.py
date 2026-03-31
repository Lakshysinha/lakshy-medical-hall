from datetime import date
from pathlib import Path
import tempfile
import unittest

from pharmacy_app import PaymentMode, PharmacyService, Role, SqliteStateStore, ValidationError


class PharmacyServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PharmacyService()
        self.med = self.service.add_medicine(
            role=Role.OWNER_ADMIN,
            name="Paracetamol 650",
            generic_composition="Acetaminophen",
            brand="PCM",
            manufacturer="ACME Pharma",
            label_notes="Pain relief",
            code_value="QR-PCM-650",
        )
        self.batch = self.service.add_batch(
            role=Role.OWNER_ADMIN,
            medicine_id=self.med.medicine_id,
            batch_no="B-001",
            mfg_date=date(2025, 1, 1),
            exp_date=date(2027, 1, 1),
            quantity=10,
            rate=5.0,
        )

    def test_search_availability_logic(self):
        hit = self.service.search_medicine("Para")
        miss = self.service.search_medicine("Unknown")
        self.assertEqual(hit["status"], "Medicine Available")
        self.assertEqual(miss["status"], "No medicine available")

    def test_date_validation_logic(self):
        with self.assertRaises(ValidationError):
            self.service.add_batch(
                role=Role.OWNER_ADMIN,
                medicine_id=self.med.medicine_id,
                batch_no="B-002",
                mfg_date=date(2026, 1, 1),
                exp_date=date(2025, 1, 1),
                quantity=5,
                rate=5.0,
            )

    def test_low_stock_threshold_logic(self):
        self.service.create_sale(
            role=Role.STAFF_BILLING,
            payment_mode=PaymentMode.CASH,
            items=[{"batch_id": self.batch.batch_id, "quantity_sold": 8}],
        )
        short_list = self.service.low_stock_short_list()
        self.assertEqual(len(short_list), 1)
        self.assertEqual(short_list[0]["quantity"], 2)

    def test_sales_calculation_and_payment_split(self):
        self.service.create_sale(
            role=Role.STAFF_BILLING,
            payment_mode=PaymentMode.CASH,
            items=[{"batch_id": self.batch.batch_id, "quantity_sold": 2, "unit_rate": 5.0}],
        )
        self.service.create_sale(
            role=Role.STAFF_BILLING,
            payment_mode=PaymentMode.ONLINE,
            items=[{"batch_id": self.batch.batch_id, "quantity_sold": 1, "unit_rate": 5.0}],
        )
        summary = self.service.daily_summary(date.today())
        self.assertEqual(summary["total_medicines_sold"], 3)
        self.assertEqual(summary["total_sales_amount"], 15.0)
        self.assertEqual(summary["cash_total"], 10.0)
        self.assertEqual(summary["online_total"], 5.0)

    def test_sale_cannot_exceed_stock(self):
        with self.assertRaises(ValidationError):
            self.service.create_sale(
                role=Role.STAFF_BILLING,
                payment_mode=PaymentMode.CASH,
                items=[{"batch_id": self.batch.batch_id, "quantity_sold": 999}],
            )

    def test_state_persists_across_restart_with_sqlite_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "pharmacy.db")
            store = SqliteStateStore(db_path)
            service_a = PharmacyService(state_store=store)

            medicine = service_a.add_medicine(
                role=Role.OWNER_ADMIN,
                name="Cetirizine",
                generic_composition="Cetirizine Hydrochloride",
                brand="CTZ",
                manufacturer="ACME Pharma",
                label_notes="Anti-allergic",
                code_value="QR-CTZ-10",
            )
            batch = service_a.add_batch(
                role=Role.OWNER_ADMIN,
                medicine_id=medicine.medicine_id,
                batch_no="C-100",
                mfg_date=date(2025, 2, 1),
                exp_date=date(2027, 2, 1),
                quantity=12,
                rate=3.0,
            )
            service_a.create_sale(
                role=Role.STAFF_BILLING,
                payment_mode=PaymentMode.ONLINE,
                items=[{"batch_id": batch.batch_id, "quantity_sold": 2}],
                customer_name="Test Customer",
            )

            service_b = PharmacyService(state_store=store)
            self.assertEqual(len(service_b.medicines), 1)
            self.assertEqual(len(service_b.batches), 1)
            self.assertEqual(len(service_b.sales), 1)
            self.assertEqual(service_b.batches[batch.batch_id].quantity, 10)
            self.assertEqual(service_b.scan_code("QR-CTZ-10")["name"], "Cetirizine")


if __name__ == "__main__":
    unittest.main()
