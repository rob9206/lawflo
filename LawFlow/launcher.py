"""Packaged LawFlow launcher for Windows one-click install."""

from __future__ import annotations

import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path


PLACEHOLDER_KEY = "sk-ant-your-key-here"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        default_root = Path(sys.executable).resolve().parent
        return Path(getattr(sys, "_MEIPASS", default_root))
    return Path(__file__).resolve().parent


def _runtime_root() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "LawFlow"
    return Path(__file__).resolve().parent


def _get_api_key(env_path: Path) -> str:
    if not env_path.exists():
        return ""

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.partition("=")[2].strip().strip('"').strip("'")
    return ""


def _write_api_key(env_path: Path, api_key: str) -> None:
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("ANTHROPIC_API_KEY="):
            lines[i] = f"ANTHROPIC_API_KEY={api_key}"
            found = True
            break

    if not found:
        lines.append(f"ANTHROPIC_API_KEY={api_key}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prompt_for_api_key() -> str:
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        key = simpledialog.askstring(
            "LawFlow setup",
            "Enter your Anthropic API key:",
            parent=root,
        )
        root.destroy()
        return (key or "").strip()
    except Exception:
        return input("Enter your Anthropic API key: ").strip()


def _ensure_env_file(runtime_root: Path, bundle_root: Path) -> Path:
    env_path = runtime_root / ".env"
    if env_path.exists():
        return env_path

    env_example_path = bundle_root / ".env.example"
    if env_example_path.exists():
        shutil.copyfile(env_example_path, env_path)
    else:
        env_path.write_text(
            f"ANTHROPIC_API_KEY={PLACEHOLDER_KEY}\n",
            encoding="utf-8",
        )
    return env_path


def _ensure_runtime_ready() -> tuple[Path, Path]:
    bundle_root = _bundle_root()
    runtime_root = _runtime_root()
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "data" / "uploads").mkdir(parents=True, exist_ok=True)
    (runtime_root / "data" / "processed").mkdir(parents=True, exist_ok=True)

    env_path = _ensure_env_file(runtime_root, bundle_root)
    api_key = _get_api_key(env_path)
    if not api_key or api_key == PLACEHOLDER_KEY:
        api_key = _prompt_for_api_key()
        if not api_key:
            raise SystemExit("Anthropic API key is required to start LawFlow.")
        _write_api_key(env_path, api_key)

    return bundle_root, runtime_root


def main() -> None:
    bundle_root, runtime_root = _ensure_runtime_ready()
    os.chdir(runtime_root)
    os.environ["LAWFLOW_ENV_PATH"] = str(runtime_root / ".env")

    from api.app import create_app
    from api.config import config

    static_dir = bundle_root / "frontend" / "dist"
    static_dir_value = str(static_dir) if static_dir.exists() else None
    app = create_app(static_dir=static_dir_value)

    launch_url = f"http://127.0.0.1:{config.PORT}"
    threading.Timer(1.2, lambda: webbrowser.open(launch_url)).start()
    app.run(host="127.0.0.1", port=config.PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
