import os
import git
from git import Actor
from github import Github
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
from pyngrok import ngrok
import requests

# Configuration
GITHUB_HOOK_TOKEN = os.getenv("GITHUB_HOOK_TOKEN")
if not GITHUB_HOOK_TOKEN:
    raise ValueError("GITHUB_HOOK_TOKEN environment variable is not set. Please set it with 'export GITHUB_HOOK_TOKEN=your_token'")
REPO_NAME = "lovable-mock-repo"
LOCAL_REPO_PATH = "./mock_repo"
LOVABLE_BOT_NAME = "lovable-bot"
PORT = 5001  # Changed to 5001 to avoid AirPods conflict

# Initialize Flask app for webhook and UI
app = Flask(__name__)
CORS(app, resources={r"/prompt": {"origins": "http://localhost:5173"}})  # Allow React on port 5173
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173"])

# Global to store ngrok tunnel URL
NGROK_WEBHOOK_URL = None

# Prompt history store (in-memory, no timestamps)
prompt_history = []
last_manual_commit_time = None

# Step 1: Initialize Git Repo and Push to GitHub
def init_repo(webhook_url):
    global NGROK_WEBHOOK_URL
    NGROK_WEBHOOK_URL = webhook_url  # Store for reuse

    g = Github(GITHUB_HOOK_TOKEN)
    user = g.get_user()
    try:
        github_repo = user.get_repo(REPO_NAME)
        print(f"Repository '{REPO_NAME}' already exists, using it.")
    except:
        print(f"Repository '{REPO_NAME}' does not exist, creating it.")
        github_repo = user.create_repo(REPO_NAME, auto_init=False)

    if not os.path.exists(LOCAL_REPO_PATH):
        os.makedirs(LOCAL_REPO_PATH)
        repo = git.Repo.init(LOCAL_REPO_PATH)
        
        bot_author = Actor("lovable-bot", "bot@lovable.dev")
        with open(os.path.join(LOCAL_REPO_PATH, "prompts.txt"), "w") as f:
            f.write("Initial commit\n")
        repo.index.add(["prompts.txt"])
        repo.index.commit("Initial commit by lovable-bot", author=bot_author)
        repo.git.branch("-M", "main")
        
        origin = repo.create_remote("origin", github_repo.clone_url.replace("https://", f"https://{GITHUB_HOOK_TOKEN}@"))
        origin.push(refspec="main:main")
        repo.git.branch("--set-upstream-to=origin/main", "main")
    else:
        repo = git.Repo(LOCAL_REPO_PATH)
        origin = repo.remote("origin") if "origin" in repo.remotes else repo.create_remote("origin", github_repo.clone_url.replace("https://", f"https://{GITHUB_HOOK_TOKEN}@"))
        repo.git.branch("-M", "main")
        try:
            origin.pull("main")
        except:
            origin.push(refspec="main:main")
        repo.git.branch("--set-upstream-to=origin/main", "main")

    hooks = github_repo.get_hooks()
    webhook_exists = any(hook.config["url"] == webhook_url for hook in hooks)
    if not webhook_exists:
        config = {"url": webhook_url, "content_type": "json"}
        events = ["push"]
        github_repo.create_hook("web", config, events, active=True)
        print(f"Webhook created at {webhook_url}")
    else:
        print(f"Webhook already exists at {webhook_url}")

    return repo, github_repo

# Step 2: Simulate Lovable Prompt Handling
def handle_prompt(prompt, repo):
    global prompt_history
    prompt_history.append(prompt)  # Just the prompt, no timestamp
    
    bot_author = Actor("lovable-bot", "bot@lovable.dev")
    
    with open(os.path.join(LOCAL_REPO_PATH, "prompts.txt"), "a") as f:
        f.write(f"{prompt}\n")
    repo.index.add(["prompts.txt"])
    repo.index.commit(f"Prompt: {prompt} by {LOVABLE_BOT_NAME}", author=bot_author)
    repo.remote("origin").push()

# Step 3: Webhook Handler for Manual Commits
@app.route("/webhook", methods=["POST"])
def webhook():
    global last_manual_commit_time, prompt_history
    
    payload = request.json
    if not payload or "commits" not in payload:
        return jsonify({"status": "ignored"}), 200
    
    manual_diffs = []
    for commit in payload["commits"]:
        author = commit["author"]["username"] if "username" in commit["author"] else commit["author"]["name"]
        if author != LOVABLE_BOT_NAME:
            commit_sha = commit["id"]
            diff_url = f"https://api.github.com/repos/{payload['repository']['full_name']}/commits/{commit_sha}"
            headers = {
                "Authorization": f"token {GITHUB_HOOK_TOKEN}",
                "Accept": "application/vnd.github.v3.diff"
            }
            response = requests.get(diff_url, headers=headers)
            if response.status_code == 200:
                diff_lines = response.text.splitlines()
                changes = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]
            else:
                changes = [f"Failed to fetch diff: {response.status_code}"]
            
            manual_diffs.append(changes)
    
    if manual_diffs:
        fine_tune_data = {
            "manual_diffs": manual_diffs,
            "prompt_history": prompt_history
        }
        
        with open("fine_tune_data.json", "a") as f:
            f.write(json.dumps(fine_tune_data) + "\n")
        print("Fine-tune data packaged:", fine_tune_data)

        # Emit WebSocket event for real-time updates
        socketio.emit('update_finetune', fine_tune_data)
    
    return jsonify({"status": "processed"}), 200

# Step 4: New Endpoint for Prompt Submission
@app.route("/prompt", methods=["POST"])
def submit_prompt():
    data = request.json
    if not data or "prompt" not in data:
        return jsonify({"error": "Prompt is required"}), 400
    
    prompt = data["prompt"]
    # Use existing repo if available, reinitialize if not
    if os.path.exists(LOCAL_REPO_PATH):
        repo = git.Repo(LOCAL_REPO_PATH)
    else:
        repo, _ = init_repo(NGROK_WEBHOOK_URL)  # Use stored ngrok URL
    handle_prompt(prompt, repo)
    
    return jsonify({"message": "Prompt processed", "prompt_history": prompt_history})

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    socketio.emit('test', {'message': 'Hello from server'})

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == "__main__":
    # Start ngrok tunnel once
    ngrok_tunnel = ngrok.connect(PORT, bind_tls=True)
    NGROK_WEBHOOK_URL = f"{ngrok_tunnel.public_url}/webhook"
    print(f"ngrok tunnel established: {NGROK_WEBHOOK_URL}")
    
    repo, github_repo = init_repo(NGROK_WEBHOOK_URL)
    
    handle_prompt("Add a login page", repo)
    handle_prompt("Fix the button styling", repo)
    
    print(f"Webhook server running at {NGROK_WEBHOOK_URL}")
    socketio.run(app, host="0.0.0.0", port=PORT)