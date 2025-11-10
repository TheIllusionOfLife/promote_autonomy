# Creating the Architecture Diagram for Hackathon Submission

## Quick Start - Use the SVG File

The easiest option is to use the provided SVG file directly:

```bash
# The SVG file is ready to use (in repository root)
./architecture-diagram.svg
```

**To convert SVG to PNG for submission:**

### Option 1: Using Inkscape (Command Line)
```bash
# Install inkscape if not available
# sudo apt-get install inkscape

# Convert to high-resolution PNG
inkscape architecture-diagram.svg --export-filename=architecture-diagram.png --export-width=2400
```

### Option 2: Using Online Converter
1. Go to [CloudConvert SVG to PNG](https://cloudconvert.com/svg-to-png)
2. Upload `architecture-diagram.svg`
3. Set width to 2400px
4. Download the PNG

### Option 3: Use GitHub to Render
1. Commit the SVG file to your repository
2. GitHub will render it automatically in README.md
3. Right-click the rendered image → Save As PNG

---

## Alternative: Create in draw.io (Professional Look)

If you want to customize the diagram, use draw.io:

### Step 1: Open draw.io
- Go to [draw.io web app](https://app.diagrams.net/)
- Or use [draw.io desktop app](https://www.diagrams.net/)

### Step 2: Create New Diagram
- Choose "Blank Diagram"
- Set canvas size to 1200x900 pixels

### Step 3: Add Components (Copy this structure)

#### Top Row - User Flow
1. **User** (Circle, gray, 60x60)
   - Icon: person icon
   - Label: "User"

2. **Frontend** (Rectangle, blue #4285f4, 140x80)
   - Line 1: "Frontend"
   - Line 2: "Next.js"
   - Line 3: "Cloud Run"
   - Line 4: "Port 3000" (smaller font)

3. **Strategy Agent** (Rectangle, blue #4285f4, 160x80)
   - Line 1: "Strategy Agent"
   - Line 2: "FastAPI + Gemini"
   - Line 3: "Cloud Run"
   - Line 4: "Port 8000" (smaller font)

4. **Firebase Auth** (Rectangle, gray #9aa0a6, 140x60)
   - Line 1: "Firebase Auth"
   - Line 2: "ID Token Verification"

#### Middle Row - Data Layer
5. **Firestore** (Rectangle, green #34a853, 140x70)
   - Line 1: "Firestore"
   - Line 2: "State Management"
   - Line 3: "Real-time Sync" (smaller)

6. **Pub/Sub** (Rectangle, green #34a853, 160x70)
   - Line 1: "Pub/Sub"
   - Line 2: "creative-tasks"
   - Line 3: "Agent Communication" (smaller)

#### Creative Agent Section (Large Container)
7. **Creative Agent Container** (Rectangle, light gray #f1f3f4, 500x280)
   - Border: 2px
   - Title: "Creative Agent - ADK Multi-Agent System"

8. **Creative Agent Main** (Rectangle, blue #4285f4, 180x60)
   - Line 1: "Creative Agent"
   - Line 2: "FastAPI + ADK"
   - Line 3: "Cloud Run (Port 8001)"

9. **ADK Coordinator Container** (Rectangle, yellow-ish #fff8e1, 250x220)
   - Border: orange #f29900, 2px
   - Title: "ADK Coordinator"
   - Subtitle: "Creative Director"
   - Model: "LlmAgent (Gemini 2.5 Flash)"

10-12. **Three Sub-Agents** (Rectangles, yellow #fbbc04, 70x50 each)
    - "Copy Writer Agent"
    - "Image Creator Agent"
    - "Video Producer Agent"

13-15. **Vertex AI Services** (Rectangles, red #ea4335, 70x60 each)
    - "Gemini 2.5 Flash - Captions"
    - "Imagen 4.0 - Images"
    - "Veo 3.0 - Videos"

16. **Cloud Storage** (Rectangle, green #34a853, 140x70)
    - Line 1: "Cloud Storage"
    - Line 2: "Generated Assets"
    - Line 3: "(Public URLs)"

#### HITL Workflow (Right Side)
17. **HITL Container** (Rectangle, light green #e8f5e9, 350x150)
   - Title: "Human-in-the-Loop Workflow"

18-20. **Workflow States** (Rectangles, white with borders, 90x40 each)
    - "Pending Approval"
    - "Processing (Generating)"
    - "Completed (Assets)"
    - Connect with arrows →

#### Key Features Box
21. **Features Container** (Rectangle, light gray #f1f3f4, 350x360)
    - Title: "Key Features"
    - Bullet points:
      - 🎯 Multi-Agent System
      - ☁️ Cloud Run Services
      - 🤖 Google AI Models
      - 🔒 Security
      - ⚡ Performance

### Step 4: Add Arrows and Flow

**Main Flow (thick blue arrows #1a73e8):**
1. User → Frontend: "1. Submit Goal"
2. Frontend → Strategy: "2. Generate Plan"
3. Strategy → Pub/Sub: "5. Publish"
4. Pub/Sub → Creative: "6. Push"

**Data Flow (regular arrows #5f6368):**
5. Strategy → Firestore: "3. Save Job"
6. Firestore → Frontend: "4. Listen"
7. Sub-agents → Vertex AI (dashed lines)
8. Vertex AI → Cloud Storage: "7. Upload Assets"
9. Cloud Storage → Frontend: "8. Display Results"

**Authentication (dashed arrow):**
10. Firebase Auth → Strategy: "Verify"

### Step 5: Add Legend (Bottom)

Create a small legend box showing:
- Blue box = Cloud Run Service
- Red box = Vertex AI Model
- Green box = Data Storage
- Yellow box = ADK Agent

### Step 6: Export

1. File → Export As → PNG
2. Settings:
   - Zoom: 200% (for high resolution)
   - Border Width: 10px
   - Background: White
   - Transparent: No
3. Download the PNG

---

## Color Palette (for consistency)

Use these exact Google Cloud colors:

| Component | Color | Hex |
|-----------|-------|-----|
| Cloud Run | Blue | #4285f4 |
| Cloud Run Border | Dark Blue | #1a73e8 |
| Vertex AI | Red | #ea4335 |
| Vertex AI Border | Dark Red | #c5221f |
| Data Layer | Green | #34a853 |
| Data Layer Border | Dark Green | #188038 |
| ADK Agents | Yellow | #fbbc04 |
| ADK Border | Orange | #f29900 |
| User/Auth | Gray | #9aa0a6 |
| Text | White | #ffffff |
| Text (on light) | Dark Gray | #202124 |
| Background | Light Gray | #f1f3f4 |

---

## Tips for Best Results

1. **High Resolution**: Export at 2x or 3x zoom for crisp text
2. **Consistent Spacing**: Use grid (10px) for alignment
3. **Font**: Use Arial or Roboto for Google Cloud consistency
4. **File Size**: Aim for <2MB for web display
5. **Aspect Ratio**: Keep it landscape (4:3 or 16:9)

---

## What to Include in Devpost Submission

Upload the PNG to Devpost as your "Architecture Diagram". Make sure it shows:

✅ All 3 Cloud Run services clearly labeled
✅ ADK multi-agent coordinator with 3 sub-agents
✅ Data flow arrows showing HITL workflow
✅ Google Cloud services (Firestore, Pub/Sub, Storage)
✅ Vertex AI models (Gemini, Imagen, Veo)
✅ Security components (Firebase Auth)
✅ Legend explaining colors/components

The diagram should tell the story of how your multi-agent system works at a glance!
