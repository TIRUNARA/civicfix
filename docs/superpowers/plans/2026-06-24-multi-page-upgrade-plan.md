# CivicFix Multi-Page Platform Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the CivicFix single-page application into a clean multi-page web platform with dedicated personal dashboard, map explorer, report creation wizard, and citizen leaderboards.

**Architecture:** We will add four HTML template routes to the FastAPI backend (`main.py`) serving static files under `templates/`. User state will be persisted client-side in `localStorage` across page navigations.

**Tech Stack:** FastAPI, Leaflet.js, TailwindCSS, Google Sign-In, OpenStreetMap Nominatim.

---

## 📂 File Architecture Map

*   **Modify**: `civicfix/main.py` (Add `/report`, `/map`, `/leaderboard` template endpoints)
*   **Create**: `civicfix/templates/dashboard.html` (Serves the personal dashboard `/`)
*   **Create**: `civicfix/templates/map.html` (Serves the interactive map explorer `/map`)
*   **Create**: `civicfix/templates/report.html` (Serves the reporting wizard `/report`)
*   **Create**: `civicfix/templates/leaderboard.html` (Serves citizen standings `/leaderboard`)

---

## 🛠️ Step-by-Step Execution Tasks

### Task 1: FastAPI Router Configurations

**Files:**
- Modify: `civicfix/main.py:314-318`
- Create: `civicfix/templates/dashboard.html`
- Create: `civicfix/templates/map.html`
- Create: `civicfix/templates/report.html`
- Create: `civicfix/templates/leaderboard.html`

- [ ] **Step 1: Write placeholder HTML templates**
  Create basic placeholder templates for each new view:
  `templates/dashboard.html`: `<html><body><h1>Dashboard</h1></body></html>`
  `templates/map.html`: `<html><body><h1>Map Explorer</h1></body></html>`
  `templates/report.html`: `<html><body><h1>Report Hazard</h1></body></html>`
  `templates/leaderboard.html`: `<html><body><h1>Leaderboard</h1></body></html>`

- [ ] **Step 2: Add template routes to `main.py`**
  Modify `main.py` at the end to serve the new pages:
  ```python
  @app.get("/", response_class=HTMLResponse)
  async def serve_dashboard():
      with open("templates/dashboard.html", "r") as f:
          return HTMLResponse(content=f.read())

  @app.get("/map", response_class=HTMLResponse)
  async def serve_map():
      with open("templates/map.html", "r") as f:
          return HTMLResponse(content=f.read())

  @app.get("/report", response_class=HTMLResponse)
  async def serve_report():
      with open("templates/report.html", "r") as f:
          return HTMLResponse(content=f.read())

  @app.get("/leaderboard", response_class=HTMLResponse)
  async def serve_leaderboard():
      with open("templates/leaderboard.html", "r") as f:
          return HTMLResponse(content=f.read())
  ```

- [ ] **Step 3: Run FastAPI locally and test routes**
  Run: `python3 -m uvicorn main:app --reload --port 8000`
  Verify that `/`, `/map`, `/report`, and `/leaderboard` resolve successfully in the browser.

- [ ] **Step 4: Commit router configurations**
  ```bash
  git add civicfix/main.py civicfix/templates/dashboard.html civicfix/templates/map.html civicfix/templates/report.html civicfix/templates/leaderboard.html
  git commit -m "feat: add template endpoints for multi-page routing"
  ```

---

### Task 2: Create Global Header & Theme Defaults

**Files:**
- Modify: `civicfix/templates/dashboard.html`
- Modify: `civicfix/templates/map.html`
- Modify: `civicfix/templates/report.html`
- Modify: `civicfix/templates/leaderboard.html`

- [ ] **Step 1: Define CSS Head & Shared Scripts**
  Include Outfit and Inter Google fonts, Leaflet assets, and Tailwind setup:
  ```html
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>CivicFix</title>
      <script src="https://cdn.tailwindcss.com"></script>
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
      <style>
          body { font-family: 'Inter', sans-serif; background-color: #020617; color: #f8fafc; }
          h1, h2, h3 { font-family: 'Outfit', sans-serif; }
          .glass-panel { background: rgba(11, 15, 25, 0.8); backdrop-filter: blur(12px); border: 1px border-white/10; }
      </style>
  </head>
  ```

- [ ] **Step 2: Add Global Navigation Header to all templates**
  ```html
  <header class="glass-panel sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-white/10">
      <div class="flex items-center gap-3">
          <span class="text-xl font-bold text-[#00E5B0] tracking-wider uppercase">CivicFix</span>
      </div>
      <nav class="flex items-center gap-6 text-sm font-semibold text-slate-300">
          <a href="/" class="hover:text-white transition-colors">Dashboard</a>
          <a href="/map" class="hover:text-white transition-colors">Map Explorer</a>
          <a href="/leaderboard" class="hover:text-white transition-colors">Leaderboard</a>
      </nav>
      <div class="flex items-center gap-4">
          <a href="/report" class="bg-[#00E5B0] hover:bg-[#00c294] text-slate-950 font-bold px-4 py-2 rounded-xl transition-all shadow-lg text-sm">📸 Report Hazard</a>
          <div id="authContainer" class="flex items-center gap-2"></div>
      </div>
  </header>
  ```

- [ ] **Step 3: Define Auth Shared Script snippet**
  Ensure all pages read `currentUser` from `localStorage` to display header login state and avatar details:
  ```javascript
  let currentUser = JSON.parse(localStorage.getItem("currentUser") || "null");
  function renderHeaderAuth() {
      const container = document.getElementById("authContainer");
      if (currentUser) {
          container.innerHTML = `
              <div class="flex items-center gap-2">
                  <img src="${currentUser.avatar || 'https://www.gravatar.com/avatar?d=mp'}" class="w-8 h-8 rounded-full border border-white/20">
                  <span class="text-xs font-semibold text-slate-200 hidden md:inline">${currentUser.name}</span>
                  <button onclick="logout()" class="text-xs text-red-400 hover:text-red-300 ml-2">Logout</button>
              </div>
          `;
      } else {
          container.innerHTML = `
              <button onclick="triggerLogin()" class="text-xs text-slate-300 hover:text-white border border-white/20 px-3 py-1.5 rounded-lg">Sign In</button>
          `;
      }
  }
  function logout() {
      localStorage.removeItem("currentUser");
      window.location.href = "/";
  }
  ```

- [ ] **Step 4: Verify Header UI render**
  Open the webapp, log in using mock credentials on `/`, and verify that navigating to `/map` preserves the login visual state in the header.

- [ ] **Step 5: Commit Navigation files**
  ```bash
  git add civicfix/templates/
  git commit -m "feat: add global responsive navigation bar and theme variables"
  ```

---

### Task 3: Build Personal Dashboard (`/`)

**Files:**
- Modify: `civicfix/templates/dashboard.html`

- [ ] **Step 1: Build Welcome & Mock Login Overlay**
  Display a login dialog for unauthenticated visitors, showing public civic stats ("Total Reports Fixed: X", "Active Citizens: Y").
  Create Auth Trigger:
  ```javascript
  function triggerLogin() {
      // Show Google Login & Mock Login dialog wrapper
  }
  ```

- [ ] **Step 2: Implement Personal Metrics Cards Grid**
  Displays 4 metrics cards for logged-in users:
  1. Total Reports Filed (from dynamic query)
  2. Issues Resolved (status matches 'Resolved')
  3. Leaderboard Points
  4. Active Rank

- [ ] **Step 3: Build Dynamic Uploads Table Feed**
  Call backend endpoint `/api/reports/my-reports/{email}` and map reports. Columns: Report ID, Image preview, Timestamp, Department, Status Badge (color-coded).
  Clicking a row opens a details panel showing the uploaded image, AI diagnostic tags, description, and resolution details (including Before vs. After comparison slider if Resolved).

- [ ] **Step 4: Test Dashboard Flow**
  Run FastAPI server. Complete mock login. Verify user-specific list displays correctly.

- [ ] **Step 5: Commit Dashboard Page**
  ```bash
  git add civicfix/templates/dashboard.html
  git commit -m "feat: implement personal dashboard page with user stats and upload list"
  ```

---

### Task 4: Build Map Explorer (`/map`)

**Files:**
- Modify: `civicfix/templates/map.html`

- [ ] **Step 1: Set up Split View Grid**
  Set up a side-by-side flex layout where the left column houses filter sliders and address inputs, and the right column houses the `#map` wrapper with zero height layout overrides.

- [ ] **Step 2: Add OSM Nominatim geocoding input**
  Implement debounced address suggestions pointing to `https://nominatim.openstreetmap.org/search`. Selecting a search suggestion pans and zooms the map.

- [ ] **Step 3: Implement Filter Controls & Tooltips**
  Map layers should filter dynamically on state changes:
  *   Filter checkboxes for Status and Department.
  *   Map markers get bound tooltips displaying ID, Department, and Status in clean text:
      ```javascript
      marker.bindTooltip(`<b>${r.id}</b><br>${r.department} (${r.status})`);
      ```
  *   Scale control: `L.control.scale().addTo(map);`
  *   Monospace Coordinate Widget: Shows current map center coordinates.

- [ ] **Step 4: Test Map Navigation & Search**
  Search for "Bengaluru" in the input field, select the result, and ensure the map zooms to the coordinates.

- [ ] **Step 5: Commit Map Explorer Page**
  ```bash
  git add civicfix/templates/map.html
  git commit -m "feat: implement split-pane map explorer with OSM geocoding search and filter panels"
  ```

---

### Task 5: Build Dedicated Reporting Wizard (`/report`)

**Files:**
- Modify: `civicfix/templates/report.html`

- [ ] **Step 1: Build Stage 1 Image Capture UI**
  Card featuring drag-and-drop file target and click trigger. Displays QR code side section pointing to dynamic token session for remote mobile phone uploads.

- [ ] **Step 2: Implement Stage 2 AI Diagnostic Progress Loader**
  Trigger `/api/reports/analyze` post-upload. Show animated step progress logging: "Uploading Image..." -> "Running Gemini Analysis..." -> "Generating Metadata...".

- [ ] **Step 3: Implement Stage 3 Verification Form**
  Form displaying the image alongside inputs for latitude, longitude, description, department, priority, and tags. Auto-fill using AI output. Submit calls `/api/reports/submit` and redirects back to `/`.

- [ ] **Step 4: Test Reporting Flow**
  Upload a hazard image. Watch the loader log details. Verify input tags. Confirm the redirection back to dashboard.

- [ ] **Step 5: Commit Reporting Page**
  ```bash
  git add civicfix/templates/report.html
  git commit -m "feat: implement dedicated multi-stage reporting page with AI analysis preview"
  ```

---

### Task 6: Build Standings Leaderboard (`/leaderboard`)

**Files:**
- Modify: `civicfix/templates/leaderboard.html`

- [ ] **Step 1: Fetch and Render Leaderboard Table**
  Fetch leaderboard rankings from `/api/reports/leaderboard`.
  Render clean table mapping Avatar, Name, Reports Filed, and Total Points. Highlight the top 3 spots using golden podium card grids.

- [ ] **Step 2: Render Global Fix Statistics**
  Show static widgets summarizing total municipal complaints resolved.

- [ ] **Step 3: Test Leaderboard loading**
  Check leaderboard displays user metrics correctly.

- [ ] **Step 4: Commit Leaderboard Page**
  ```bash
  git add civicfix/templates/leaderboard.html
  git commit -m "feat: implement gamified standings leaderboard page"
  ```
