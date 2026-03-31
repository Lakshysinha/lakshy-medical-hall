# Medicine Inventory App – 5 Phase Plan of Action

## Project Objective
Build a medicine inventory app where staff can:
- Add and manage medicine records with full label details.
- Store MFG date, EXP date, and batch number.
- Scan medicine strip codes (printed on the back of tablet strips) to fetch details.
- Search medicine from a search tab and instantly know if medicine is available or not.
- Auto-add medicines with quantity **<= 3** to a separate **Short List** section.

---

## Phase 1: Requirement Finalization & Workflow Mapping
1. Finalize mandatory medicine fields:
   - Medicine Name
   - Generic/Composition
   - Brand
   - Manufacturer
   - Batch No.
   - MFG Date
   - EXP Date
   - Quantity
   - Price (optional)
   - Label/Notes
   - Code/QR value
2. Finalize app sections:
   - Dashboard
   - Add Medicine
   - Search Tab
   - Scanner
   - Short List (Low Stock)
3. Define search-tab behavior:
   - If medicine found: display **"Medicine Available"** with details.
   - If not found: display **"No medicine available"**.
4. Define low-stock rule:
   - Quantity <= 3 triggers automatic entry in Short List.
5. Create UI wireframes and user journey.

---

## Phase 2: Data Model & System Design
1. Database tables design:
   - `medicines`
   - `batches`
   - `stock_transactions`
   - `short_list`
   - `users`
2. Core constraints:
   - Batch number should be unique per batch entry.
   - EXP Date must be later than MFG Date.
   - Quantity cannot be negative.
3. Define key backend APIs:
   - Add medicine entry
   - Update stock
   - Get medicine by name
   - Get medicine by batch no
   - Get medicine by scanned code
   - Auto-sync short list by quantity threshold
4. Security design:
   - Role-based access
   - Authenticated medicine updates

---

## Phase 3: Core Feature Development
1. Build medicine entry form with all labels and date fields.
2. Implement search tab:
   - Name-based search
   - Availability status response
   - “No medicine available” fallback message
3. Implement batch number based entry/retrieval.
4. Integrate scanner module:
   - Use camera to scan code on medicine strip back side.
   - Parse code and fetch medicine record.
5. Implement low-stock automation:
   - On add/update/sale, if quantity <= 3, auto-add to Short List.
   - If quantity goes above 3, auto-remove from Short List.

---

## Phase 4: Testing, Validation & Reliability
1. Unit tests for:
   - Search logic (available vs unavailable)
   - Short list threshold logic (<= 3)
   - Date validation (MFG/EXP)
2. Integration tests for:
   - Entry by batch number
   - Scanner to medicine mapping
   - Stock updates affecting Short List
3. UI tests:
   - Search tab messages
   - Short List section accuracy
4. Device testing for scanner camera compatibility.

---

## Phase 5: Deployment, Training & Implementation Start
1. Deploy backend + database + app frontend.
2. Configure backups, logs, and monitoring.
3. Train staff on:
   - Adding medicine
   - Searching medicine availability
   - Scanning strip code
   - Managing low stock through Short List
4. Prepare v2 enhancement backlog:
   - Barcode + QR dual support
   - Expiry alerts
   - Supplier reorder automation

---

## Implementation Note
Actual app coding should be done by following this README plan as the reference implementation roadmap.

## Permission Request
The updated 5-phase plan is now prepared with your new requirements.

Please confirm: **Do I have your permission to start coding the app implementation now?**
