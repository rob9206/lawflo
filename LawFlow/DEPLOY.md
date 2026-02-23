# Deploying LawFlow to Replit

## Quick Start

1. **Push this repo to GitHub** (or have it there already).

2. **Create a new Repl:**
   - Go to [replit.com](https://replit.com) and sign in
   - Click **Create Repl** > **Import from GitHub**
   - Paste your repository URL and click **Import**
   - Replit will detect the `.replit` config automatically

3. **Set Secrets** (in the Secrets tab, padlock icon in the sidebar):

   | Secret               | Required? | Value                                        |
   |----------------------|-----------|----------------------------------------------|
   | `FLASK_SECRET_KEY`   | Yes       | Any random string (e.g. `mysecretkey123`)    |
   | `ANTHROPIC_API_KEY`  | Optional  | Your `sk-ant-...` key (users can bring their own) |
   | `ALLOWED_ORIGINS`    | Optional  | `https://your-repl-name.replit.app`          |

4. **Click Run.** The first run takes a few minutes (installs Python + Node deps, builds the frontend). After that it starts the server.

5. **Share the URL.** Replit gives you a public URL like `https://your-repl-name.replit.app`. Send it to anyone.

## How It Works

- `build.sh` installs Python dependencies and builds the React frontend into `frontend/dist/`
- Gunicorn (production Python server) starts Flask on port 8080
- Flask serves both the API (`/api/*`) and the built React app (`/*`)
- Users enter their own Anthropic API key in the app's settings (stored in their browser only)

## Always-On Hosting

The free tier sleeps after inactivity (~10-30 second cold start on next visit).

For always-on hosting, use **Replit Deployments** ($7/month):
- Click **Deploy** in the top-right of your Repl
- Choose **Reserved VM** for best SQLite compatibility
- Set the same secrets as above

## Troubleshooting

**Build fails on Node/npm:**
Make sure `replit.nix` includes `pkgs.nodejs_20` and `pkgs.nodePackages.npm`.

**"Module not found" errors:**
Check that `PYTHONPATH` is set to `LawFlow` in the `.replit` `[env]` section.

**API calls return 500:**
Check the Replit console for errors. Most likely the Anthropic API key is missing or invalid. Users can set their key in the app's profile/settings page.

**Database resets on redeploy:**
SQLite data persists on Replit's filesystem between runs. If you redeploy from scratch (delete and re-import), the database resets. For production use, consider backing up `data/lawflow.db`.
