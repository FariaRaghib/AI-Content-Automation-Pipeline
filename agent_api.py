"""
Agent API Server
-----------------
Wraps all LeadQualify Python agents in a local web API.
n8n (running in Docker) calls these endpoints via HTTP instead of
trying to run Python scripts directly (which Docker can't do).

Install:
    pip install flask

Run:
    python agent_api.py

Then it stays running at http://localhost:5000
n8n reaches it via: http://host.docker.internal:5000

Endpoints:
    GET  /health                 - check server is alive
    POST /run/ideator            - runs ideator.py
    POST /run/hooks              - runs hook_writer_mock.py
    POST /run/planner            - runs planner.py
    POST /run/analyst            - runs analyst.py
    POST /run/leads              - runs dm_manager.py
    POST /run/blog               - runs blog_agent.py
    POST /run/all                - runs everything in order
    GET  /data/<filename>        - fetch a generated JSON file
"""

import subprocess
import json
import os
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

AGENTS = {
    "ideator": "ideator.py",
    "hooks": "hook_writer.py",
    "planner": "planner.py",
    "analyst": "analyst.py",
    "leads": "dm_manager.py",
    "blog": "blog_agent.py",
    "publish_blog": "devto_publisher.py",
    "publish_instagram": "instagram_publisher.py",
    "publish_linkedin": "linkedin_publisher.py",
    "fetch_comments": "instagram_comments_fetcher.py",
    "auto_reply": "instagram_auto_reply.py",
    "telegram": "telegram_bot_fixed.py",
    "blog_reply": "blog_reply_drafts.py",
}


def run_script(script_name):
    """Run a python script in the project folder, capture output."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"  # force UTF-8 so checkmarks etc. don't crash on Windows

    result = subprocess.run(
        ["python", script_name],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        encoding="utf-8",
        errors="replace"
    )
    output = {
        "script": script_name,
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

    # Special case: make Telegram delivery status explicit and unambiguous,
    # since the script can exit 0 even if the actual send silently failed.
    if script_name == "telegram_bot_fixed.py":
        combined = (result.stdout or "") + (result.stderr or "")
        if "sent to Telegram" in combined:
            output["telegram_delivered"] = True
        elif "Telegram notification failed" in combined or "Telegram API error" in combined:
            output["telegram_delivered"] = False
        else:
            output["telegram_delivered"] = "unknown - check stdout manually"

    return output


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Agent API is running"})


@app.route("/run/<agent_name>", methods=["POST", "GET"])
def run_agent(agent_name):
    if agent_name == "all":
        results = []
        for name, script in AGENTS.items():
            r = run_script(script)
            results.append(r)
            if not r["success"]:
                # Stop the chain if one fails, so you can see exactly where
                return jsonify({"completed": results, "stopped_at": name}), 500
        return jsonify({"completed": results})

    if agent_name not in AGENTS:
        return jsonify({"error": f"Unknown agent '{agent_name}'. Valid: {list(AGENTS.keys())}"}), 400

    result = run_script(AGENTS[agent_name])
    status_code = 200 if result["success"] else 500
    return jsonify(result), status_code


@app.route("/data/<filename>", methods=["GET"])
def get_data(filename):
    """Serve a generated JSON file, e.g. /data/planner_calendar.json"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": f"{filename} not found. Run the agent first."}), 404
    return send_from_directory(DATA_DIR, filename)


if __name__ == "__main__":
    print("=" * 60)
    print("LeadQualify Agent API")
    print("=" * 60)
    print(f"Project folder: {PROJECT_DIR}")
    print(f"Local URL:      http://localhost:5000")
    print(f"From n8n Docker: http://host.docker.internal:5000")
    print("=" * 60)
    print("\nEndpoints:")
    for name in AGENTS:
        print(f"  POST http://localhost:5000/run/{name}")
    print(f"  POST http://localhost:5000/run/all")
    print(f"  GET  http://localhost:5000/data/<filename>")
    print("\nLeave this running. Press CTRL+C to stop.\n")

    app.run(host="0.0.0.0", port=5000)