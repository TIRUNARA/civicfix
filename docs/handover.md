# CivicFix Project Handover

This document serves as the session handover state for the **CivicFix** infrastructure platform built for the Vibe2Ship hackathon. It summarizes the current features, live database configuration, codebase improvements, and next steps to resume development.

---

## 🚀 Live Environment & Credentials

*   **Repository:** `https://github.com/TIRUNARA/civicfix` (Public)
*   **Database Engine:** PostgreSQL (Production on Neon) / SQLite (Local Development)
*   **Active DATABASE_URL:**
    ```text
    postgresql://neondb_owner:npg_SYnM09aVotlc@ep-billowing-frog-ad0w23w1.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require
    ```
*   **Google API Keys (Gemini):** Stored in local `.env` as `GOOGLE_API_KEY_1` and `GOOGLE_API_KEY_2`.

---

## 🛠️ Key Features Implemented

### 1. Robust Dual-Database Architecture (`database.py`)
*   Supports runtime dual-mode operations (SQLite locally, PostgreSQL in production).
*   Translates query parameters dynamically (SQLite `?` to PostgreSQL `%s`) via a custom connection/cursor wrapper, allowing backend endpoints to remain database-agnostic.

### 2. AI-Powered Diagnostics & Verification (`gemini_service.py`)
*   **Submission Parsing:** Automatically analyzes uploaded photos using `gemini-2.5-flash` to extract tags, identify the responsible department, and compute initial issue priority.
*   **Resolution Verification:** Compares the original "before" photo side-by-side with the officer's "after" photo to check if the repair was completed, preventing fraudulent status updates.

### 3. Hyperlocal Map Navigation (`templates/index.html`)
*   Fully interactive Leaflet map styled with a Dark theme.
*   Added city preset jump selections, custom coordinates auto-panning, and a floating **"Center on My Location"** tracking button.

### 4. Zero-Friction Desktop & Mobile Upload Fallbacks
*   **Desktop Direct Upload:** Allows reporting directly from a computer by uploading local files. Geocoding automatically falls back to browser location or the current map center coordinates.
*   **Mobile QR Bridge & Fallback:** Generates an auto-sizing QR code (`typeNumber = 0` to prevent length overflows). If the mobile browser blocks camera access (`getUserMedia`), the UI offers a native file selector that opens the device camera or photo gallery directly.

---

## 🗃️ Current Database State
The production Neon database is initialized and pre-seeded with:
*   **7 Active/Resolved Reports:** 4 mock reports in Bengaluru (MG Road, Indiranagar, Koramangala, Jayanagar) and 3 active user reports around Delhi (Dwarka).
*   **5 Active Community Members:** Seeded on the leaderboard with score values (ranging from 10 to 150 pts).

---

## 📋 Next Action Items
1.  **Deploy to Render:** Wait for the latest commit (`abe72fb` - Auto-size QR code) to finish building on Render and confirm the live HTTPS URL.
2.  **Test the Full Flow:** 
    *   Open the live Render URL.
    *   Click **Report New Hazard**, scan the QR code with a mobile device, and use the camera/native upload option.
    *   Switch to the **Officer Portal**, upload an "after" image to resolve an issue, and verify the AI confirms resolution.
3.  **Submission Preparation:** Fill out the hackathon project submission forms using the final Render deployment link and the public GitHub repository link.
