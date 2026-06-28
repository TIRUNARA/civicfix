const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, LevelFormat, Header, Footer } = require('docx');

// Setup standard borders for tables
const borderStyle = { style: BorderStyle.SINGLE, size: 8, color: "CCCCCC" };
const borders = { top: borderStyle, bottom: borderStyle, left: borderStyle, right: borderStyle };

// Create document
const doc = new Document({
  styles: {
    default: {
      document: {
        run: {
          font: "Arial",
          size: 24, // 12pt (docx size is in half-points)
          color: "333333"
        }
      }
    },
    paragraphStyles: [
      {
        id: "Title",
        name: "Title",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 56, // 28pt
          bold: true,
          font: "Arial",
          color: "1A365D"
        },
        paragraph: {
          spacing: { before: 2000, after: 240 },
          alignment: AlignmentType.CENTER
        }
      },
      {
        id: "Subtitle",
        name: "Subtitle",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 28, // 14pt
          font: "Arial",
          color: "4A5568",
          italic: true
        },
        paragraph: {
          spacing: { before: 120, after: 2000 },
          alignment: AlignmentType.CENTER
        }
      },
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 36, // 18pt
          bold: true,
          font: "Arial",
          color: "1A365D"
        },
        paragraph: {
          spacing: { before: 360, after: 180 },
          outlineLevel: 0
        }
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 28, // 14pt
          bold: true,
          font: "Arial",
          color: "2B6CB0"
        },
        paragraph: {
          spacing: { before: 240, after: 120 },
          outlineLevel: 1
        }
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 24, // 12pt
          bold: true,
          font: "Arial",
          color: "4A5568"
        },
        paragraph: {
          spacing: { before: 180, after: 120 },
          outlineLevel: 2
        }
      },
      {
        id: "Normal",
        name: "Normal",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: {
          size: 24,
          font: "Arial"
        },
        paragraph: {
          spacing: { after: 160 }
        }
      }
    ]
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 720, hanging: 360 },
                spacing: { after: 100 }
              }
            }
          }
        ]
      },
      {
        reference: "numbers",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 720, hanging: 360 },
                spacing: { after: 100 }
              }
            }
          }
        ]
      }
    ]
  },
  sections: [
    {
      properties: {
        page: {
          size: {
            width: 12240, // US Letter
            height: 15840
          },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "CivicFix: AI-Driven Multi-Tier Municipal Triage Engine",
                  size: 18,
                  color: "718096"
                })
              ],
              tabStops: [{ type: "right", position: 9360 }],
              alignment: AlignmentType.LEFT
            })
          ]
        })
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              children: [
                new TextRun({
                  text: "Vibe2Code Hackathon Submission Document",
                  size: 18,
                  color: "718096"
                }),
                new TextRun("\t"),
                new TextRun({
                  children: [PageNumber.CURRENT],
                  size: 18,
                  color: "718096"
                })
              ],
              tabStops: [{ type: "right", position: 9360 }],
              alignment: AlignmentType.LEFT
            })
          ]
        })
      },
      children: [
        // COVER PAGE
        new Paragraph({ text: "CIVICFIX", style: "Title" }),
        new Paragraph({ text: "AI-Powered Multi-Tier Municipal Infrastructure Triage and Verification Engine", style: "Subtitle" }),
        new Paragraph({ spacing: { before: 1440 } }),
        new Paragraph({
          children: [
            new TextRun({ text: "Prepared For: ", bold: true, color: "4A5568" }),
            new TextRun("Vibe2Code Hackathon Submissions"),
          ],
          alignment: AlignmentType.CENTER
        }),
        new Paragraph({
          children: [
            new TextRun({ text: "Created By: ", bold: true, color: "4A5568" }),
            new TextRun("TIRUNARA (Shiva) & Integrity Co-Engineer"),
          ],
          alignment: AlignmentType.CENTER
        }),
        new Paragraph({
          children: [
            new TextRun({ text: "System State: ", bold: true, color: "4A5568" }),
            new TextRun("Release Production v1.2.0"),
          ],
          alignment: AlignmentType.CENTER
        }),
        new Paragraph({
          children: [
            new TextRun({ text: "Date: ", bold: true, color: "4A5568" }),
            new TextRun("June 2026"),
          ],
          alignment: AlignmentType.CENTER,
          spacing: { after: 2000 }
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // PAGE 2: EXECUTIVE SUMMARY & PROBLEM STATEMENT
        new Paragraph({ text: "1. Executive Summary & Problem Statement", heading: HeadingLevel.HEADING_1 }),
        new Paragraph({
          children: [
            new TextRun("In modern urban environments, public infrastructure hazards—such as open potholes, overflowing sewage, fractured streetlights, and illicit dumping—significantly impact citizen safety, local commerce, and municipal efficiency. Traditional reporting methods suffer from major operational bottlenecks: slow manual triage, fragmented communication across municipal departments, fraudulent reporting, and lack of verified resolution tracking. Administrative backlogs mean citizen reports can take weeks to route, verify, and resolve.")
          ]
        }),
        new Paragraph({
          children: [
            new TextRun("CivicFix resolves these bottlenecks by deploying an autonomous, agentic multi-tier pipeline designed to streamline the lifecycle of municipal repairs. Utilizing the official Google GenAI SDK for multi-modal vision triage and side-by-side verification, CivicFix bridges the gap between citizens, municipal administrators, field workers, and compliance reviewers.")
          ]
        }),
        new Paragraph({
          children: [
            new TextRun("Key components of the platform include:")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Hyperlocal Map Navigation: ", bold: true }),
            new TextRun("A responsive Leaflet-based dark interface tracking active hazards, offering single-click centering and city presets.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Zero-Friction Camera Interfaces: ", bold: true }),
            new TextRun("Desktop uploads paired with an auto-sizing mobile QR bridge, providing automatic camera selection and gallery fallbacks.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Multi-Modal AI Quality Control: ", bold: true }),
            new TextRun("Image validation checks to verify photo clarity and relevance, requesting clarification dynamically if an image is blurred or unrelated.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Double-Blind AI Verification: ", bold: true }),
            new TextRun("Side-by-side comparative analysis matching original issue photos with resolution photos to guarantee repair authenticity before closing tickets.")
          ]
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // PAGE 3: TECHNICAL ARCHITECTURE & PIPELINE
        new Paragraph({ text: "2. Technical Architecture & Pipeline", heading: HeadingLevel.HEADING_1 }),
        new Paragraph({
          children: [
            new TextRun("CivicFix operates as a stage-wise execution pipeline that coordinates roles across the platform. Below is the detailed breakdown of the 4 stages represented in the system architecture:")
          ]
        }),
        // TABLE OF STAGES
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1800, 2500, 5060],
          rows: [
            // Header Row
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 1800, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Stage", bold: true, color: "1A365D" })] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2500, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Core Components", bold: true, color: "1A365D" })] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5060, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Operational Capabilities", bold: true, color: "1A365D" })] })]
                })
              ]
            }),
            // Row 1
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 1800, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Stage 1:", bold: true })] }),
                    new Paragraph({ children: [new TextRun({ text: "Reporting", bold: true })] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 2500, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun("Citizen Web Portal")] }),
                    new Paragraph({ children: [new TextRun("AI Quality Control")] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 5060, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Citizen submits geotagged reports and uploads hazard photos. Proactive AI quality control verifies image clarity and sharpness, requesting instant retakes for blurry/unrelated files.")] })]
                })
              ]
            }),
            // Row 2
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 1800, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Stage 2:", bold: true })] }),
                    new Paragraph({ children: [new TextRun({ text: "AI Triage", bold: true })] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 2500, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun("Triage AI Engine")] }),
                    new Paragraph({ children: [new TextRun("Officer Dashboard")] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 5060, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Triage engine classifies reports into 8 distinct departments and assigns initial severity and cost estimates. Officers can review, edit, or override triage statuses.")] })]
                })
              ]
            }),
            // Row 3
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 1800, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Stage 3:", bold: true })] }),
                    new Paragraph({ children: [new TextRun({ text: "Execution", bold: true })] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 2500, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun("Workers' Portal")] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 5060, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Field crews access tasks matching their specialized department, accept tickets, navigate to coordinate points, and update repair progress states.")] })]
                })
              ]
            }),
            // Row 4
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 1800, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun({ text: "Stage 4:", bold: true })] }),
                    new Paragraph({ children: [new TextRun({ text: "Resolution", bold: true })] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 2500, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [
                    new Paragraph({ children: [new TextRun("Fixer Portal")] }),
                    new Paragraph({ children: [new TextRun("AI Verification")] })
                  ]
                }),
                new TableCell({
                  borders,
                  width: { size: 5060, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Workers submit resolution photos of completed repairs. The AI verification engine runs side-by-side analysis, confirming the hazard is resolved before closing the ticket.")] })]
                })
              ]
            })
          ]
        }),
        new Paragraph({ spacing: { before: 240 } }),
        new Paragraph({ children: [new PageBreak()] }),

        // PAGE 4: CORE ENGINEERING INNOVATIONS
        new Paragraph({ text: "3. Core Engineering Innovations", heading: HeadingLevel.HEADING_1 }),
        new Paragraph({ text: "Dual-Database Replication Layer (database.py)", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("CivicFix implements a unique, custom-written dual-database interface. In local environments, the platform runs on light-weight SQLite. In cloud production (deployed on Render), it dynamically connects to serverless PostgreSQL on Neon. To ensure the FastAPI endpoints remain completely agnostic of the database engine, the wrapper automatically intercepts SQL strings at runtime. It replaces SQL-style question mark query placeholders ('?') with positional parameter bindings ('%s') required by PostgreSQL, allowing seamless database hot-swaps without code refactoring.")
          ]
        }),
        new Paragraph({ text: "Multi-Modal AI Diagnostics & Verification (gemini_service.py)", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("The system leverages the modern Google GenAI SDK (migrated to the official 'google-genai' schema) with the 'gemini-2.5-flash' model to handle complex cognitive tasks:")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Automated Classification: ", bold: true }),
            new TextRun("Extracts tags, locates the hazard, maps it to a standardized 2-Tier taxonomy (8 departments), and computes initial hazard severity.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "Before/After Side-by-Side Comparison: ", bold: true }),
            new TextRun("When a field officer marks a ticket as resolved, the Gemini model runs a vision comparative analysis to verify the hazard has been fixed, preventing false sign-offs.")
          ]
        }),
        new Paragraph({ text: "Mobile QR Bridge & Native Camera Fallbacks", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("CivicFix solves desktop reporting limitations through an auto-sizing QR code wizard. Scanning the QR code routes mobile users to a session draft upload endpoint. If a user's mobile browser blocks WebRTC camera API calls, the interface automatically triggers a native file upload selector configured with capture tags, opening the camera rolls and galleries directly.")
          ]
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // PAGE 5: DATABASE SCHEMAS & API ENDPOINTS
        new Paragraph({ text: "4. Database Schemas & API Endpoints", heading: HeadingLevel.HEADING_1 }),
        new Paragraph({ text: "Core Database Table Schema Definitions", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("The CivicFix SQLite/PostgreSQL schema consists of four principal tables managing reports, user authentication, logs, and public achievements:")
          ]
        }),
        // TABLE OF SCHEMAS
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2000, 2000, 5360],
          rows: [
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Table Name", bold: true, color: "1A365D" })] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Primary Key / Index", bold: true, color: "1A365D" })] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5360, type: WidthType.DXA },
                  shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun({ text: "Description of Fields & Purpose", bold: true, color: "1A365D" })] })]
                })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("reports")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("id (INTEGER)")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5360, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Stores hazard tickets: title, description, category, department, coordinates (lat/lng), image_path, status, cost_estimate, severity, and timestamps.")] })]
                })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("users")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("id / email")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5360, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Handles logins: username, email (UNIQUE), hashed_password, and user role (Citizen, Officer, Reviewer, Fixer).")] })]
                })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("leaderboard")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("email (UNIQUE)")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5360, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Tracks civic points awarded for reporting issues or completing repairs. Uses ON CONFLICT (email) upserting logic.")] })]
                })
              ]
            }),
            new TableRow({
              children: [
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("activity_log")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 2000, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("id (INTEGER)")] })]
                }),
                new TableCell({
                  borders,
                  width: { size: 5360, type: WidthType.DXA },
                  margins: { top: 80, bottom: 80, left: 120, right: 120 },
                  children: [new Paragraph({ children: [new TextRun("Tracks structural updates, officer manual overrides, worker dispatches, and verification statuses with full timestamps.")] })]
                })
              ]
            })
          ]
        }),
        new Paragraph({ spacing: { before: 240 } }),
        new Paragraph({ text: "Primary Backend API Routes (main.py)", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("The FastAPI core exposes clean REST endpoints:")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "GET /api/reports: ", bold: true }),
            new TextRun("Queries active, triaged, and resolved reports with coordinates for the Leaflet front-end map.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "POST /api/reports/submit: ", bold: true }),
            new TextRun("Submits new reports. Automatically triggers the Gemini vision triage parser if an image is attached.")
          ]
        }),
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          children: [
            new TextRun({ text: "POST /api/reports/resolve/{id}: ", bold: true }),
            new TextRun("Accepts resolution proof images from officers and dispatches to Gemini verification before updating DB statuses.")
          ]
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // PAGE 6: HARDENING, COMPLIANCE & SECURITY
        new Paragraph({ text: "5. Hardening, Compliance & Security", heading: HeadingLevel.HEADING_1 }),
        new Paragraph({ text: "Symlink & Path Traversal Prevention", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("To pass production security guidelines, the backend includes strict file validation. When static files or report images are requested, the filepath is evaluated using Python's pathlib module. The script resolves absolute paths, validating that the resolved target remains within the boundaries of the designated upload directory. Target paths pointing to external symlinks or using dot-dot path traversal sequences ('../') are rejected with a 403 Forbidden HTTP exception.")
          ]
        }),
        new Paragraph({ text: "SQL Parameterization", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("To protect the dual-database schema from SQL Injection, the query mapper is built on parameterized execution. The SQLite/PostgreSQL adapter forbids raw string concatenation for user-supplied fields. All parameters are compiled into tuple mappings and passed directly to cursor execution blocks, guaranteeing data/code separation.")
          ]
        }),
        new Paragraph({ text: "Image Deserialization Safety", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("Database rows store image references as JSON array strings. To prevent deserialization crashes, the resolution validation endpoints contain strict parsing loops: it deserializes raw column strings to verify array structures and confirms that files exist on local volumes before attempting to run PIL conversions.")
          ]
        }),
        new Paragraph({ text: "Leaderboard PostgreSQL Upserts", heading: HeadingLevel.HEADING_2 }),
        new Paragraph({
          children: [
            new TextRun("The leaderboard table constraints were updated to enforce email-level uniqueness in production. The upsert logic in PostgreSQL uses 'ON CONFLICT (email) DO UPDATE' to dynamically increment citizen and officer reward metrics, protecting table indices and avoiding unique key constraint violations.")
          ]
        })
      ]
    }
  ]
});

// Compile and write document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("../CivicFix_Project_Documentation.docx", buffer);
  console.log("Document generated successfully as 'CivicFix_Project_Documentation.docx'");
}).catch(err => {
  console.error("Failed to generate document:", err);
});
