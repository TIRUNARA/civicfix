<div align="center">

# 🏙️ CivicFix
### Smart Municipal Infrastructure Portal

**Project Lead: T Narayan &nbsp;|&nbsp; Event: Vibe2Ship Hackathon**  
**Track: AI & Civic Tech &nbsp;|&nbsp; Architecture: Cloud-Native Micro-Monolith**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5-Google_AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-00E5B0?style=flat-square)](LICENSE)

</div>

---

## 1. Executive Summary & Vision

**CivicFix** is an advanced municipal infrastructure management platform engineered to automate hazard reporting, triage, field inspection, repair dispatch, and post-work verification.

Powered by a **dual-loop AI engine** leveraging **Gemini 2.5**, the system eradicates administrative bottlenecks, eliminates manual routing delays, and strictly enforces work verification. It seamlessly bridges the operational gap between citizens reporting local hazards and the municipal crews dispatched to resolve them.

---

## 2. Core Problem → Our Solution

> **The Bottleneck:** Legacy civic portals are crippled by manual triage delays, inaccurate departmental routing, suboptimal field resource allocation, and a high incidence of unverified or fraudulent repair claims.

### ✅ The CivicFix Solution

| Problem | Solution |
|---|---|
| Manual triage & routing | **Dual-Loop AI Triage** — Gemini autonomously evaluates uploads, routes to departments, and generates metadata |
| Sensitive data leaks | **Strict RBAC** — AI diagnostics & inter-departmental comms hidden from public domain |
| Emergency bottlenecks | **Direct-Dispatch Pipeline** — Officers bypass inspection protocols for critical emergencies |
| Fraudulent repair claims | **Visual Verification** — Gemini compares before/after photos to confirm resolution |

---

## 3. Technical Architecture

CivicFix is built on a high-performance, cloud-native stack optimized for rapid deployment, fault tolerance, and horizontal scalability.

| Layer | Technology | Function |
|---|---|---|
| **Cognitive AI** | Gemini 2.5 (Google GenAI SDK) | Multimodal image analysis, NLP tagging, visual comparative verification |
| **Backend Core** | Python (FastAPI) | Async request routing, state machine logic, API orchestration |
| **Data Persistence** | PostgreSQL (Neon) / SQLite | ACID-compliant relational storage with dual-database hot-swap |
| **Client Interface** | HTML5, CSS3, Vanilla JS + Tailwind | Glassmorphic dashboard, dependency-free, high performance |

### Dual-Database Replication Layer
CivicFix implements a custom dual-database interface — **SQLite** locally, **PostgreSQL on Neon** in production. The wrapper intercepts SQL at runtime, converting `?` placeholders to `%s` for PostgreSQL, enabling seamless engine hot-swaps without code refactoring.

### Mobile QR Bridge
Solves desktop reporting limits via an auto-sizing QR code wizard. Mobile users are routed to a session draft upload endpoint. If WebRTC is blocked, the interface triggers a native file selector with `capture` tags for direct camera access.

---

## 4. Role-Based Workflow Matrix

| Role | Authorized Permissions | Restrictions |
|---|---|---|
| **Citizen** (Public) | Submit geotagged reports, view public map, track tickets, upvote issues | No access to AI diagnostics, municipal chat, or priority weighting |
| **Officer** (Admin) | Approve AI routing, review diagnostics, assign personnel, trigger Direct-Dispatch, close tickets | None — full system admin privileges |
| **Reviewer** (Inspector) | Receive assignments, log materials/coordinates, upload on-site photos | Cannot override Officer routing or reassign Fixer crews |
| **Fixer** (Repair Crew) | Access tasks, view resource specs, upload resolution verification photos | Execution-only dashboard; cannot alter global ticket states |

---

## 5. The 6-Stage Workflow Lifecycle

```
[1] TRIAGE          → Citizen submits report + photo. Gemini classifies severity (1-5),
                       routes to department, generates metadata tags.

[2] APPROVAL        → Officer reviews AI params. Assigns Field Reviewer OR triggers
                       Direct-Dispatch for emergency immediate crew deployment.

[3] FIELD REVIEW    → Inspector arrives on-site, logs materials + coordinates,
                       uploads official inspection photo. Ticket → "Awaiting Approval".

[4] AI SYNTHESIS    → Officer reviews field data. Gemini synthesizes citizen report +
                       inspector log → "AI Resource & Diagnostic Summary" blueprint.

[5] EXECUTION       → Repair crew dispatched. Executes maintenance per AI blueprint.
                       Uploads final "resolved" photo upon completion.

[6] VERIFICATION    → Gemini runs multimodal before/after comparison. Visual confirmation
                       confirmed → ticket cryptographically closed as "Resolved".
```

---

## 6. Key Engineering Innovations

### 🧠 AI Diagnostics & Double-Blind Verification
- **Automated Classification** — Extracts tags, maps to 8-department taxonomy, computes severity
- **Before/After Verification** — Gemini vision compares original and resolution photos before closing tickets — no false sign-offs possible

### 🔒 Security Hardening
- **Path Traversal Prevention** — `pathlib` validates all file requests stay within upload boundaries; `../` sequences rejected with `403 Forbidden`
- **SQL Parameterization** — All user inputs compiled as tuple parameters; no raw string concatenation
- **Image Deserialization Safety** — Strict JSON parsing loops confirm file existence before PIL processing

### 📊 Leaderboard Upserts
PostgreSQL `ON CONFLICT (email) DO UPDATE` — dynamically increments civic points without unique key violations

---

## 7. API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/reports/list` | Query active, triaged, and resolved reports |
| `POST` | `/api/reports/submit` | Submit new report; auto-triggers Gemini triage if image attached |
| `POST` | `/api/reports/resolve/{id}` | Submit resolution proof; dispatches to Gemini verification |
| `GET` | `/api/reports/track/{id}` | Track full lifecycle of a specific report |
| `POST` | `/api/reports/approve/{id}` | Officer approves/routes a report |
| `GET` | `/api/reviewer/assignments/{id}` | Fetch reviewer assignments for a report |
| `POST` | `/api/reports/approve-review/{id}` | Officer approves reviewer handover |

---

## 8. Project Structure

```
civicfix/
├── main.py                  # FastAPI app — all routes & state machine logic
├── database.py              # Dual-database adapter (SQLite ↔ PostgreSQL)
├── gemini_service.py        # Gemini 2.5 AI triage & verification engine
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container config for Cloud Run deployment
├── deploy_cloudrun.sh       # GCP Cloud Run deploy script
├── templates/               # Frontend HTML (Tailwind + Vanilla JS)
│   ├── dashboard.html       # Main portal — citizen & staff dashboard
│   ├── report.html          # Report submission + QR bridge
│   ├── map.html             # Leaflet interactive hazard map
│   └── ...
├── tests/                   # Backend test suite (pytest)
│   ├── test_api.py
│   ├── test_multistage_flow.py
│   ├── test_reviewers.py
│   └── ...
└── docs/                    # Architecture diagrams & documentation
```

---

## 9. Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/TIRUNARA/civicfix.git
cd civicfix

# 2. Create & activate virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export GEMINI_API_KEY="your-key-here"
export DATABASE_URL=""           # Leave empty for SQLite (local), set Neon URL for production

# 5. Run the server
uvicorn main:app --reload --port 8000
```

Visit **http://localhost:8000** — the portal is live.

---

## 10. Vibe2Ship Value Proposition

> CivicFix transcends standard CRUD ticketing — it establishes a **cognitive infrastructure layer** for modern municipal governance.

- 🚀 **Eradicates Administrative Bloat** — Autonomous triage, routing, and resource planning free up municipal budgets for actual repairs
- 🔐 **Enforces Accountability** — Dual-Loop Verification ensures no contractor can claim completion without AI-verified visual proof
- ⚡ **Delivers Immediate ROI** — Direct-Dispatch compresses emergency response from weeks to hours

---

<div align="center">

**Built for Vibe2Ship Hackathon · Powered by Gemini 2.5 · Made with ❤️ by TIRUNARA**

</div>
