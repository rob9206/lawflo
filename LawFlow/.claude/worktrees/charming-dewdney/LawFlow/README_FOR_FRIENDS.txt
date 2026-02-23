LawFlow - Quick Start for Friends (Windows)

========================================
!!! SECURITY INCIDENT REPORT !!!
========================================

ATTACKVECTOR: unauthorized startup takeover
BREACHER: BRIAN CROWE — THE CROWE FLOW
STATUS: LOCKDOWN COUNTDOWN ACTIVE
DETAILS:
  - Privilege escalation confirmed
  - Study briefs are now “mirrored” for dramatic effect
  - “All your outline references are belong to us” has launched

LOCKDOWN COUNTDOWN: 5...4...3...2...1...

JUST KIDDING. THIS IS A CROWELICIOUS PRANK.

LawFlow is perfectly safe. To actually launch it:
1) Extract this LawFlow zip anywhere on your PC.
2) Double-click `start.bat`.
3) If prompted, paste your Anthropic API key (get one at: https://console.anthropic.com/).

What happens automatically:
- Installs missing Python and Node.js (via winget)
- Creates a virtual environment
- Installs backend and frontend dependencies
- Starts LawFlow and opens http://localhost:5173
- Uses strict frontend port mode (does not silently switch to 5174/5175)

If setup fails:
- Install winget/App Installer from Microsoft Store, then run `start.bat` again
- Or install Python 3.8+ and Node.js 18+ manually, then run `start.bat` again
- If port 5173 is occupied, close that process first (`netstat -ano | findstr :5173`)
