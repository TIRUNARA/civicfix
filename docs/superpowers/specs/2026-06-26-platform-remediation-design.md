# CivicFix Platform Remediation Design Spec

## 1. Objectives & Scope
Finalize the CivicFix web application to make it resilient, aesthetically premium, and securely role-restricted.

---

## 2. Technical Architecture & Components

### 2.1 Storage & Database Persistence
* **Current state**: Local SQLite database and uploaded images are saved to `/tmp/`, causing data loss on server/PC restarts.
* **Remediation**:
  * **Database path**: Move default database path to the project root directory `./civicfix.db`.
  * **Uploads directory**: Move default uploaded images directory to `./uploads/`. Both are already git-ignored.
  * **FastAPI Mounts**: Update static file mounts from `/tmp/uploads` to the persistent `./uploads` folder.

### 2.2 Google Authentication & Role Routing
* **Current state**: Dummy client ID and manual dropdown toggle for Citizen/Officer modes.
* **Remediation**:
  * **GSI Client ID**: Make the client ID configurable via a meta-tag or default fallback if `.env` is absent.
  * **Role Assignment Rules**:
    * Authenticated Google accounts with emails containing `officer` (e.g., `officer@gmail.com`), `admin`, or ending with `.gov` / `city.gov` / `civicfix.org` are assigned the `officer` role.
    * All other accounts are assigned the `citizen` role.
  * **Role Enforcement UI**:
    * If `currentUser.role === 'officer'`, automatically enable and select "Officer Portal".
    * If `currentUser.role === 'citizen'`, hide the dropdown completely and prevent access to officer functionality.

### 2.3 Visual Polish & Premium UI Animations
* **Aesthetics**: Apply standard Outfit/Inter font styling with deep slate/cyan/emerald glassmorphic schemes.
* **Animations**:
  * **Processing Scanner**: While a report is in `"Processing"` status, render a glowing holographic scanline that moves vertically across the card thumbnail.
  * **Loading Indicator**: Integrate smooth CSS-based spinning rings for file uploads.
  * **Micro-interactions**: Subtle scale transforms (`scale-102`) and smooth opacity shifts for buttons and cards.

### 2.4 Gemini Classification Tuning
* **Current state**: Standard classification works correctly, but we want to monitor it to prevent multi-department false positives for complex issues.
* **Remediation**: Defer prompt modifications since the existing prompt is performing well. We will leave `gemini_service.py` intact to avoid regressions, but document safety rules for future iterations.

---

## 3. Test Plan
* Validate database initialization creates `./civicfix.db` correctly.
* Run existing pytest tests to verify offline mocks pass.
