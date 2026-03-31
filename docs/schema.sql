CREATE TABLE users (
  user_id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('owner_admin', 'pharmacist', 'staff_billing'))
);

CREATE TABLE medicines (
  medicine_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  generic_composition TEXT NOT NULL,
  brand TEXT NOT NULL,
  manufacturer TEXT NOT NULL,
  label_notes TEXT,
  code_value TEXT NOT NULL UNIQUE
);

CREATE TABLE batches (
  batch_id INTEGER PRIMARY KEY,
  medicine_id INTEGER NOT NULL REFERENCES medicines(medicine_id),
  batch_no TEXT NOT NULL,
  mfg_date DATE NOT NULL,
  exp_date DATE NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  rate NUMERIC(10,2) NOT NULL,
  UNIQUE (medicine_id, batch_no),
  CHECK (exp_date > mfg_date)
);

CREATE TABLE stock_transactions (
  stock_txn_id INTEGER PRIMARY KEY,
  batch_id INTEGER NOT NULL REFERENCES batches(batch_id),
  txn_type TEXT NOT NULL,
  quantity_delta INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales (
  sale_id INTEGER PRIMARY KEY,
  customer_name TEXT,
  payment_mode TEXT NOT NULL CHECK (payment_mode IN ('cash', 'online')),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sale_items (
  sale_item_id INTEGER PRIMARY KEY,
  sale_id INTEGER NOT NULL REFERENCES sales(sale_id),
  medicine_id INTEGER NOT NULL REFERENCES medicines(medicine_id),
  batch_id INTEGER NOT NULL REFERENCES batches(batch_id),
  quantity_sold INTEGER NOT NULL CHECK (quantity_sold >= 0),
  tablets_sold INTEGER NOT NULL DEFAULT 0,
  strips_sold INTEGER NOT NULL DEFAULT 0,
  unit_rate NUMERIC(10,2) NOT NULL,
  total_cost NUMERIC(10,2) NOT NULL
);

CREATE TABLE payment_transactions (
  payment_txn_id INTEGER PRIMARY KEY,
  sale_id INTEGER NOT NULL REFERENCES sales(sale_id),
  payment_mode TEXT NOT NULL CHECK (payment_mode IN ('cash', 'online')),
  amount NUMERIC(10,2) NOT NULL
);

CREATE TABLE customer_records (
  record_id INTEGER PRIMARY KEY,
  sale_id INTEGER NOT NULL REFERENCES sales(sale_id),
  customer_name TEXT,
  transaction_date DATE NOT NULL
);

CREATE TABLE audit_logs (
  audit_id INTEGER PRIMARY KEY,
  action TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
