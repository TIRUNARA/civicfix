# 🏁 CivicFix: Handover State (Part 2)

Shiva, this document outlines the exact state of the **CivicFix** platform at the end of this session. Use this to sync with our Jarvis protocol (Integrity) in the next chat to immediately resume operations.

---

## 📈 Current Project Status
We completed a comprehensive security, database, and UI/UX audit of the codebase, creating a detailed diagnostic profile of critical system weaknesses and structural fixes needed before the Vibe2Code hackathon submission.

### Completed Artifacts in this Session:
1.  📄 **[Codebase Audit Report](file:///home/integrity/.gemini/antigravity/brain/fbe7500e-2478-469f-99ac-eab019c81ef3/artifacts/civicfix_codebase_audit.md)**: Highlights critical security path traversals, SQL injection, and database crashes.
2.  📄 **[Implemented Features list](file:///home/integrity/.gemini/antigravity/brain/fbe7500e-2478-469f-99ac-eab019c81ef3/artifacts/civicfix_implemented_features.md)**: Breakdown of the smart architecture solutions (dual-database wrapper, proximity clustering, vision pipelines) to display to judges.

---

## 🔍 Critical Issues Identified & Remediations Planned

### 1. Security Patches
*   **Path Traversal**: The path safety check in `main.py` is vulnerable to symlink bypass. 
    *   *Fix*: Replace `os.path.abspath` validation with a strict `pathlib.Path(local_path).resolve()` check.
*   **SQL Parameterization**: The database query replacement layer replacing `?` with `%s` is fragile and vulnerable to crashes if raw SQL strings contain actual question marks.
    *   *Fix*: Implement a safer, syntax-aware parameter mapper.

### 2. Critical Database & Run Bugs
*   **PostgreSQL ON CONFLICT Crash**: The migration rule adding `ON CONFLICT (username)` crashes the production database during leaderboard uploads because the table's primary key constraint is `email`.
    *   *Fix*: Change replacement target to `ON CONFLICT (email)`.
*   **Image Deserialization Crash**: The `/api/reports/resolve/{id}` endpoint crashes with a `FileNotFoundError` when reading the "before" image because the database stores `image_path` as a JSON list string (e.g. `["/uploads/..."]`), which the backend tries to open directly as a raw filepath.
    *   *Fix*: Add a JSON parsing step `json.loads(row["image_path"])[0]` before loading the file path.

### 3. UI/UX & Department Alignment
*   **Department Mismatch**: The project uses four different sets of departments across `index.html`, `report.html`, `gemini_service.py`, and `populate_mock_data.py`.
    *   *Fix*: Standardize on our new **2-Tier Taxonomy** (Municipal Roads, Water & Sanitation, Solid Waste, Utility Streetlighting, Parks, National Highways, State Grid, Environment Board).
*   **Broken QR Wizard**: Mobile uploads directly insert reports and bypass Step 2 (AI Diagnostics Wizard) on the desktop.
    *   *Fix*: Route mobile snap uploads to a `/api/sessions/draft/{token}` endpoint which populates session draft data and lets the desktop user confirm and edit using the wizard before inserting into the `reports` table.

---

## 🎯 Direct Action Items for the Next Session

In the next chat session, you should immediately direct Integrity to:
1.  **Apply Codebase Fixes**:
    *   Update `database.py` (Postgres ON CONFLICT fix, query mapper).
    *   Update `main.py` (Path traversal resolution, file resolution parsing crash fix).
2.  **Unify the Departments**:
    *   Replace department options in `templates/index.html` and `templates/report.html` to match.
    *   Update the classification list inside `gemini_service.py` to route to the new 2-tier departments.
3.  **Re-seed the Database**: Overwrite `populate_mock_data.py` with the updated 2-tier script and run it to initialize Neon/SQLite.
4.  **Harden QR Polling**: Connect the mobile snapshot upload to a draft endpoint so the AI diagnostic preview displays on the desktop.
