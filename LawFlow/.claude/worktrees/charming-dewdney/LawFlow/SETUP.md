# LawFlow Setup Guide

## True One-Click Install (Windows, no Python/Node required)

To share LawFlow with a friend who has no dev tools installed:

1. On your dev machine, build the installer:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build_windows_installer.ps1
   ```
2. Send your friend `installer\output\LawFlowSetup.exe`.
3. Your friend runs the installer and launches LawFlow from the Start Menu/Desktop.

On first launch, LawFlow prompts for the Anthropic API key and then opens in the browser automatically.

---

## One-Click Dev Start (Windows)

After completing the prerequisites below, you can still **double-click `start.bat`** for local development.

---

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.8+** (check with `python --version` or `python3 --version`)
- **Node.js 18+** and npm (check with `node --version` and `npm --version`)
- **Anthropic API Key** - Get one from https://console.anthropic.com/

## Step 1: Clone/Download the Project

If you received this as a zip file, extract it. If it's a git repo, clone it:

```bash
git clone <repository-url>
cd LawFlow
```

## Step 2: Backend Setup

### 2.1 Create a Python Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Configure Environment Variables

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```
   (On macOS/Linux: `cp .env.example .env`)

2. Open `.env` in a text editor and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```

3. Optionally adjust other settings (the defaults should work for local development)

### 2.4 Create Required Directories

The app will create these automatically, but you can create them manually:

```bash
mkdir -p data/uploads
mkdir -p data/processed
```

(On Windows PowerShell: `New-Item -ItemType Directory -Path data\uploads, data\processed`)

## Step 3: Frontend Setup

### 3.1 Navigate to Frontend Directory

```bash
cd frontend
```

### 3.2 Install Node Dependencies

```bash
npm install
```

## Step 4: Run the Application

You need to run **both** the backend and frontend servers.

### Terminal 1: Start the Backend (Flask)

```bash
# Make sure you're in the LawFlow root directory and venv is activated
cd c:\Dev\LawFlow  # or your path
venv\Scripts\activate  # Windows
# OR: source venv/bin/activate  # macOS/Linux

python api/app.py
```

**Note:** The backend runs on port **5002** by default (not 5000).

The backend should start on `http://127.0.0.1:5002`

### Terminal 2: Start the Frontend (Vite)

```bash
# Navigate to frontend directory
cd frontend

npm run dev -- --strictPort
```

The frontend should start on `http://localhost:5173`.
With strict port mode enabled, startup fails if `5173` is already in use (it will not fall back to `5174`, `5175`, etc.).

## Step 5: Access the Application

Open your browser and go to: **http://localhost:5173**

The frontend will automatically proxy API requests to the backend.

## Troubleshooting

### Backend won't start
- Make sure your virtual environment is activated
- Check that port 5002 is not already in use
- Verify your `.env` file exists and has `ANTHROPIC_API_KEY` set
- Check for Python errors in the terminal

### Frontend won't start
- Make sure you ran `npm install` in the `frontend` directory
- Check that port 5173 is not already in use (`netstat -ano | findstr :5173`)
- Stop the process using that port, then retry (`taskkill /PID <pid> /F` on Windows)
- Try deleting `node_modules` and running `npm install` again

### API calls failing
- Make sure both servers are running
- Check that the backend is on port 5002 (not 5000)
- Verify your Anthropic API key is valid
- Check browser console for CORS errors

### Database issues
- The SQLite database will be created automatically at `data/lawflow.db`
- If you need to reset: delete `data/lawflow.db` and restart the backend

## Important Notes

⚠️ **This is a development prototype** - not production-ready. See `.cursor/plans/production_readiness_assessment_c2506607.plan.md` for details.

- The app uses SQLite (single file database)
- No authentication is required (all endpoints are public)
- Debug mode is enabled by default
- CORS is configured for localhost only

## Stopping the Application

- Press `Ctrl+C` in both terminal windows to stop the servers
- Deactivate the Python virtual environment: `deactivate`

## Next Steps

Once running, you can:
- Upload documents (PDF, DOCX, PPTX)
- Use the tutor feature
- Track your progress
- Build knowledge graphs

Enjoy using LawFlow! 🎓
