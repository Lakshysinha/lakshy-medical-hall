from datetime import date
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib import request

from pharmacy_app import (
    AuthError,
    AuthService,
    PaymentMode,
    PharmacyAPI,
    PharmacyService,
    Role,
    SqliteStateStore,
    ValidationError,
    build_server,
)


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


class PharmacyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PharmacyService()
        self.auth = AuthService(
            {
                "owner": {"password": "owner123", "role": Role.OWNER_ADMIN.value},
                "billing": {"password": "bill123", "role": Role.STAFF_BILLING.value},
            }
        )
        self.api = PharmacyAPI(service=self.service, auth=self.auth)
        self.owner_token = self.api.login("owner", "owner123")["token"]
        self.billing_token = self.api.login("billing", "bill123")["token"]

    def test_api_login_and_medicine_flow(self):
        med = self.api.add_medicine(
            token=self.owner_token,
            payload={
                "name": "Amoxicillin",
                "generic_composition": "Amoxicillin",
                "brand": "AMX",
                "manufacturer": "ACME Pharma",
                "label_notes": "Antibiotic",
                "code_value": "QR-AMX-500",
            },
        )
        batch = self.api.add_batch(
            token=self.owner_token,
            payload={
                "medicine_id": med["medicine_id"],
                "batch_no": "A-500",
                "mfg_date": "2025-01-01",
                "exp_date": "2027-01-01",
                "quantity": 20,
                "rate": 12.5,
            },
        )
        sale = self.api.create_sale(
            token=self.billing_token,
            payload={
                "payment_mode": "cash",
                "items": [{"batch_id": batch["batch_id"], "quantity_sold": 2}],
                "customer_name": "Ravi",
            },
        )
        self.assertEqual(sale["total_amount"], 25.0)
        search = self.api.search_medicine(token=self.owner_token, query="Amoxi")
        self.assertEqual(search["status"], "Medicine Available")
        summary = self.api.daily_summary(token=self.owner_token, day_iso=date.today().isoformat())
        self.assertEqual(summary["total_medicines_sold"], 2)

    def test_token_expiry_and_logout(self):
        short_auth = AuthService(
            {"owner": {"password": "owner123", "role": Role.OWNER_ADMIN.value}},
            token_ttl_seconds=1,
        )
        api = PharmacyAPI(service=PharmacyService(), auth=short_auth)
        token = api.login("owner", "owner123")["token"]
        api.logout(token)
        with self.assertRaises(AuthError):
            api.search_medicine(token=token, query="abc")


class PharmacyHttpTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        service = PharmacyService()
        auth = AuthService(
            {
                "owner": {"password": "owner123", "role": Role.OWNER_ADMIN.value},
                "billing": {"password": "bill123", "role": Role.STAFF_BILLING.value},
            }
        )
        api = PharmacyAPI(service=service, auth=auth)
        self.server = build_server("127.0.0.1", 0, api)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _post(self, path: str, payload: dict, token: str | None = None) -> dict:
        req = request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
            method="POST",
        )
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, path: str, token: str) -> dict:
        req = request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_http_transport_end_to_end(self):
        owner_token = self._post("/auth/login", {"username": "owner", "password": "owner123"})["token"]
        billing_token = self._post("/auth/login", {"username": "billing", "password": "bill123"})["token"]

        med = self._post(
            "/medicines",
            {
                "name": "Dolo",
                "generic_composition": "Paracetamol",
                "brand": "DOLO",
                "manufacturer": "ACME",
                "label_notes": "Fever",
                "code_value": "QR-DOLO",
            },
            token=owner_token,
        )
        batch = self._post(
            "/batches",
            {
                "medicine_id": med["medicine_id"],
                "batch_no": "D-1",
                "mfg_date": "2025-01-01",
                "exp_date": "2027-01-01",
                "quantity": 15,
                "rate": 10.0,
            },
            token=owner_token,
        )
        self._post(
            "/sales",
            {
                "payment_mode": "online",
                "items": [{"batch_id": batch["batch_id"], "quantity_sold": 3}],
            },
            token=billing_token,
        )
        summary = self._get(f"/reports/daily?day={date.today().isoformat()}", token=owner_token)
        self.assertEqual(summary["online_total"], 30.0)
        logout = self._post("/auth/logout", {}, token=owner_token)
        self.assertEqual(logout["status"], "logged_out")


if __name__ == "__main__":
    unittest.main()
