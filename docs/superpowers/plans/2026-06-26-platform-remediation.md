# CivicFix Platform Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate the CivicFix platform's critical bugs, database resets, and UI vulnerabilities to make it persistent, beautifully animated, and role-enforced.

**Architecture:** Relocate storage paths to the workspace root for persistence, dynamically resolve role access client-side based on authenticated Google/mock email patterns, and introduce dynamic scanlines and micro-animations to modern CSS transitions.

**Tech Stack:** FastAPI, SQLite, Tailwind CSS, Leaflet JS, Google Identity Services.

---

### Task 1: Persistent Database and Upload Directory Relocation

**Files:**
- Modify: `database.py`
- Modify: `main.py`
- Modify: `test_db.py`

- [ ] **Step 1: Relocate SQLite DB Path in `database.py`**
  Modify `/home/integrity/Desktop/agent/civicfix/database.py` to change the default database path from `/tmp/civicfix.db` to a file inside the root workspace folder.
  
  ```python
  # database.py around line 89
  # Before:
  # db_path = os.environ.get("DB_PATH", "/tmp/civicfix.db")
  # After:
  db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "civicfix.db"))
  ```

- [ ] **Step 2: Update Upload Directory Paths and Fallbacks in `main.py`**
  Modify `/home/integrity/Desktop/agent/civicfix/main.py` to define a persistent upload directory within the root directory and update all occurrences of `/tmp/uploads`.
  
  ```python
  # Add UPLOAD_DIR constant at the top:
  UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))
  os.makedirs(UPLOAD_DIR, exist_ok=True)
  ```
  
  Replace all occurrences of `"/tmp/uploads"` with `UPLOAD_DIR`, and update the `/uploads/` string replacements:
  
  ```python
  # example inside async_process_report_ai:
  local_path = path.replace("/uploads/", f"{UPLOAD_DIR}/", 1)
  ```

- [ ] **Step 3: Update `test_db.py` to Use Dynamic Database Path**
  Modify `/home/integrity/Desktop/agent/civicfix/test_db.py` to clear the dynamic database path before initialization instead of the hardcoded `/tmp/civicfix.db`.
  
  ```python
  # test_db.py
  # Before:
  # if os.path.exists("/tmp/civicfix.db"):
  #     os.remove("/tmp/civicfix.db")
  # After:
  db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(database.__file__), "civicfix.db"))
  if os.path.exists(db_path):
      os.remove(db_path)
  ```

- [ ] **Step 4: Run database tests to verify passes**
  Run command: `python3 test_db.py`
  Expected output: "Test passed: Database initialized correctly and columns verified." and "SQLite to Postgres query conversion tokenizer verified."

- [ ] **Step 5: Commit changes**
  Run:
  ```bash
  git add database.py main.py test_db.py
  git commit -m "refactor: relocate database and uploads to project root for persistence"
  ```

---

### Task 2: Backend Upload Path and Mounting Adjustments

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Modify File Upload, Async Report, and Resolve Routes**
  Replace all static mentions of `"/tmp/uploads"` in the routes in `main.py` with `UPLOAD_DIR`. Specifically:
  * File paths for generated draft images.
  * Image lookup paths in background tasks.
  * Resolution image uploads.
  * Update static mounts at the bottom of the file:
  
  ```python
  # main.py around line 555
  # Before:
  # app.mount("/tmp/uploads", StaticFiles(directory="/tmp/uploads"), name="uploads_tmp")
  # app.mount("/uploads", StaticFiles(directory="/tmp/uploads"), name="uploads")
  # After:
  app.mount("/tmp/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads_tmp")
  app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
  ```

- [ ] **Step 2: Commit changes**
  Run:
  ```bash
  git add main.py
  git commit -m "feat: bind static app mounts to persistent uploads directory"
  ```

---

### Task 3: Authentication and Role Enforcement Logic

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `templates/index.html`
- Modify: `templates/map.html`

- [ ] **Step 1: Add role assignment helpers to `templates/dashboard.html`**
  Modify `/home/integrity/Desktop/agent/civicfix/templates/dashboard.html` to add the email-to-role mapper, update mock logins to offer Citizen/Officer variants, and hide/disable the role select menu for non-officers.
  
  In script tags:
  ```javascript
  function getRoleFromEmail(email) {
      if (!email) return 'citizen';
      const lower = email.toLowerCase();
      if (lower.endsWith('.gov') || lower.endsWith('city.gov') || lower.endsWith('civicfix.org') || lower.includes('officer') || lower === 'shiva@civicfix.org' || lower === 'officer@gmail.com') {
          return 'officer';
      }
      return 'citizen';
  }
  ```
  
  Update `triggerMockLogin(role)` to accept a role argument:
  ```javascript
  function triggerMockLogin(role = 'citizen') {
      const isOfficer = role === 'officer';
      currentUser = {
          email: isOfficer ? "officer@civicfix.org" : "shiva@civicfix.org",
          name: isOfficer ? "Officer Shiva" : "Shiva (Citizen)",
          avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${isOfficer ? 'officershiva' : 'shiva'}`,
          role: isOfficer ? 'officer' : 'citizen'
      };
      localStorage.setItem("user", JSON.stringify(currentUser));
      showToast(`🔑 Mock ${role} authentication session started!`, "success");
      window.location.reload();
  }
  ```
  
  Replace the mock login button in HTML:
  ```html
  <div class="flex flex-col gap-2">
      <button onclick="triggerMockLogin('citizen')" class="w-full py-2.5 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 text-[#00E5B0] hover:from-emerald-500/20 hover:to-cyan-500/20 font-bold rounded-xl text-xs transition-all shadow-md active:scale-[0.98]">
          🔑 Instant Citizen Demo
      </button>
      <button onclick="triggerMockLogin('officer')" class="w-full py-2.5 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border border-blue-500/20 text-blue-400 hover:from-blue-500/20 hover:to-indigo-500/20 font-bold rounded-xl text-xs transition-all shadow-md active:scale-[0.98]">
          👮 Instant Officer Demo
      </button>
  </div>
  ```
  
  In `window.onload`, ensure role consistency and hide `roleToggle` if not an officer:
  ```javascript
  if (currentUser) {
      if (!currentUser.role) {
          currentUser.role = getRoleFromEmail(currentUser.email);
          localStorage.setItem("user", JSON.stringify(currentUser));
      }
      
      const roleToggle = document.getElementById("roleToggle");
      if (currentUser.role === 'officer') {
          roleToggle.classList.remove("hidden");
          // If value is citizen and user hasn't explicitly toggled, set it to officer
          if (!roleToggle.value) {
              roleToggle.value = "officer";
          }
      } else {
          roleToggle.classList.add("hidden");
          roleToggle.value = "citizen";
      }
  } else {
      document.getElementById("roleToggle").classList.add("hidden");
  }
  ```

- [ ] **Step 2: Add same role checks and buttons to `templates/index.html`**
  Modify `/home/integrity/Desktop/agent/civicfix/templates/index.html` to integrate the same `getRoleFromEmail` rules, update mock login buttons to Citizen/Officer options, and restrict/hide the `roleToggle` selection container.

- [ ] **Step 3: Add role checks to `templates/map.html`**
  Modify `/home/integrity/Desktop/agent/civicfix/templates/map.html` to load and verify roles on page load, hiding `roleToggle` unless `currentUser.role === 'officer'`.

- [ ] **Step 4: Commit auth changes**
  Run:
  ```bash
  git add templates/dashboard.html templates/index.html templates/map.html
  git commit -m "feat: implement Google/Mock authentication email role routing and menu visibility guards"
  ```

---

### Task 4: Premium UI Animations, Diagnostics Scanline & Micro-Interactions

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `templates/index.html`

- [ ] **Step 1: Inject scanning animations styles in header styles**
  Add keyframes for vertical scanning lasers to the header `<style>` blocks in both `templates/dashboard.html` and `templates/index.html`:
  
  ```css
  @keyframes scanline {
      0% { transform: translateY(-100%); opacity: 0; }
      10% { opacity: 0.8; }
      90% { opacity: 0.8; }
      100% { transform: translateY(100%); opacity: 0; }
  }
  .scanner-laser {
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, transparent, #00E5B0, transparent);
      box-shadow: 0 0 8px #00E5B0;
      animation: scanline 2.5s linear infinite;
  }
  ```

- [ ] **Step 2: Add dynamic scanner elements for processing report cards**
  In the Javascript template literal code that renders report list cards, check if `r.status === 'Processing'`. If so, inject the `.scanner-laser` div inside the card relative thumbnail container.
  
  ```javascript
  // inside render cards in templates/dashboard.html & index.html
  const isProcessing = r.status === 'Processing';
  const laserHtml = isProcessing ? `<div class="scanner-laser"></div>` : '';
  // Append inside the card media relative wrapper
  ```

- [ ] **Step 3: Refine page transitions and detail modal fade-in/scale**
  Ensure transitions use standard Tailwind CSS classes or custom transition rules (e.g. adding `transition-all duration-300 ease-out` and managing classes) to eliminate layout jumps.

- [ ] **Step 4: Commit UI animation changes**
  Run:
  ```bash
  git add templates/dashboard.html templates/index.html
  git commit -m "style: add premium holographic scanline animation for processing AI reports"
  ```
