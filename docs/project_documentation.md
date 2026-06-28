# CivicFix: AI-Driven Multi-Tier Municipal Triage and Verification Engine
**Vibe2Code Hackathon Submission Technical Overview & Architecture Blueprint**

---

## 1. Executive Summary & Problem Statement

In modern urban environments, public infrastructure hazards—such as open potholes, overflowing sewage, fractured streetlights, and illicit dumping—significantly impact citizen safety, local commerce, and municipal efficiency. Traditional reporting methods suffer from major operational bottlenecks: slow manual triage, fragmented communication across municipal departments, fraudulent reporting, and lack of verified resolution tracking. Administrative backlogs mean citizen reports can take weeks to route, verify, and resolve.

CivicFix resolves these bottlenecks by deploying an autonomous, agentic multi-tier pipeline designed to streamline the lifecycle of municipal repairs. Utilizing the official Google GenAI SDK for multi-modal vision triage and side-by-side verification, CivicFix bridges the gap between citizens, municipal administrators, field workers, and compliance reviewers.

Key components of the platform include:
*   **Hyperlocal Map Navigation**: A responsive Leaflet-based dark interface tracking active hazards, offering single-click centering and city presets.
*   **Zero-Friction Camera Interfaces**: Desktop uploads paired with an auto-sizing mobile QR bridge, providing automatic camera selection and gallery fallbacks.
*   **Multi-Modal AI Quality Control**: Image validation checks to verify photo clarity and relevance, requesting clarification dynamically if an image is blurred or unrelated.
*   **Double-Blind AI Verification**: Side-by-side comparative analysis matching original issue photos with resolution photos to guarantee repair authenticity before closing tickets.

---

## 2. Technical Architecture & Pipeline

CivicFix operates as a stage-wise execution pipeline that coordinates roles across the platform. Below is the detailed breakdown of the 4 stages represented in the system architecture:

| Stage | Core Components | Operational Capabilities |
| :--- | :--- | :--- |
| **Stage 1: Reporting** | Citizen Web Portal<br>AI Quality Control | Citizen submits geotagged reports and uploads hazard photos. Proactive AI quality control verifies image clarity and sharpness, requesting instant retakes for blurry/unrelated files. |
| **Stage 2: AI Triage** | Triage AI Engine<br>Officer Dashboard | Triage engine classifies reports into 8 distinct departments and assigns initial severity and cost estimates. Officers can review, edit, or override triage statuses. |
| **Stage 3: Execution** | Workers' Portal | Field crews access tasks matching their specialized department, accept tickets, navigate to coordinate points, and update repair progress states. |
| **Stage 4: Resolution** | Fixer Portal<br>AI Verification | Workers submit resolution photos of completed repairs. The AI verification engine runs side-by-side analysis, confirming the hazard is resolved before closing the ticket. |

---

## 3. Core Engineering Innovations

### Dual-Database Replication Layer (`database.py`)
CivicFix implements a unique, custom-written dual-database interface. In local environments, the platform runs on light-weight SQLite. In cloud production (deployed on Render), it dynamically connects to serverless PostgreSQL on Neon. To ensure the FastAPI endpoints remain completely agnostic of the database engine, the wrapper automatically intercepts SQL strings at runtime. It replaces SQL-style question mark query placeholders (`?`) with positional parameter bindings (`%s`) required by PostgreSQL, allowing seamless database hot-swaps without code refactoring.

### Multi-Modal AI Diagnostics & Verification (`gemini_service.py`)
The system leverages the modern Google GenAI SDK (migrated to the official `google-genai` schema) with the `gemini-2.5-flash` model to handle complex cognitive tasks:
*   **Automated Classification**: Extracts tags, locates the hazard, maps it to a standardized 2-Tier taxonomy (8 departments), and computes initial hazard severity.
*   **Before/After Side-by-Side Comparison**: When a field officer marks a ticket as resolved, the Gemini model runs a vision comparative analysis to verify the hazard has been fixed, preventing false sign-offs.

### Mobile QR Bridge & Native Camera Fallbacks
CivicFix solves desktop reporting limitations through an auto-sizing QR code wizard. Scanning the QR code routes mobile users to a session draft upload endpoint. If a user's mobile browser blocks WebRTC camera API calls, the interface automatically triggers a native file upload selector configured with capture tags, opening the camera rolls and galleries directly.

---

## 4. Database Schemas & API Endpoints

### Core Database Table Schema Definitions
The CivicFix SQLite/PostgreSQL schema consists of four principal tables managing reports, user authentication, logs, and public achievements:

| Table Name | Primary Key / Index | Description of Fields & Purpose |
| :--- | :--- | :--- |
| **reports** | `id` (INTEGER) | Stores hazard tickets: title, description, category, department, coordinates (lat/lng), image_path, status, cost_estimate, severity, and timestamps. |
| **users** | `id` / `email` | Handles logins: username, email (UNIQUE), hashed_password, and user role (Citizen, Officer, Reviewer, Fixer). |
| **leaderboard** | `email` (UNIQUE) | Tracks civic points awarded for reporting issues or completing repairs. Uses ON CONFLICT (email) upserting logic. |
| **activity_log** | `id` (INTEGER) | Tracks structural updates, officer manual overrides, worker dispatches, and verification statuses with full timestamps. |

### Primary Backend API Routes (`main.py`)
The FastAPI core exposes clean REST endpoints:
*   `GET /api/reports`: Queries active, triaged, and resolved reports with coordinates for the Leaflet front-end map.
*   `POST /api/reports/submit`: Submits new reports. Automatically triggers the Gemini vision triage parser if an image is attached.
*   `POST /api/reports/resolve/{id}`: Accepts resolution proof images from officers and dispatches to Gemini verification before updating DB statuses.

---

## 5. Hardening, Compliance & Security

### Symlink & Path Traversal Prevention
To pass production security guidelines, the backend includes strict file validation. When static files or report images are requested, the filepath is evaluated using Python's `pathlib` module. The script resolves absolute paths, validating that the resolved target remains within the boundaries of the designated upload directory. Target paths pointing to external symlinks or using dot-dot path traversal sequences (`../`) are rejected with a 403 Forbidden HTTP exception.

### SQL Parameterization
To protect the dual-database schema from SQL Injection, the query mapper is built on parameterized execution. The SQLite/PostgreSQL adapter forbids raw string concatenation for user-supplied fields. All parameters are compiled into tuple mappings and passed directly to cursor execution blocks, guaranteeing data/code separation.

### Image Deserialization Safety
Database rows store image references as JSON array strings. To prevent deserialization crashes, the resolution validation endpoints contain strict parsing loops: it deserializes raw column strings to verify array structures and confirms that files exist on local volumes before attempting to run PIL conversions.

### Leaderboard PostgreSQL Upserts
The leaderboard table constraints were updated to enforce email-level uniqueness in production. The upsert logic in PostgreSQL uses `ON CONFLICT (email) DO UPDATE` to dynamically increment citizen and officer reward metrics, protecting table indices and avoiding unique key constraint violations.
