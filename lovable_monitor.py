import os
import git
from git import Actor
from github import Github
from flask import Flask, request, jsonify
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
PORT = 5001

# Initialize Flask app for webhook
app = Flask(__name__)

# Prompt history store (in-memory, no timestamps)
prompt_history = []
last_manual_commit_time = None

# Step 1: Initialize Git Repo and Push to GitHub
def init_repo(webhook_url):
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
                # Extract only the added lines from the diff
                diff_lines = response.text.splitlines()
                changes = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]
            else:
                changes = [f"Failed to fetch diff: {response.status_code}"]
            
            manual_diffs.append(changes)  # Just the list of added lines
    
    if manual_diffs:
        fine_tune_data = {
            "manual_diffs": manual_diffs,
            "prompt_history": prompt_history
        }
        
        with open("fine_tune_data.json", "a") as f:
            f.write(json.dumps(fine_tune_data) + "\n")
        print("Fine-tune data packaged:", fine_tune_data)
    
    return jsonify({"status": "processed"}), 200

if __name__ == "__main__":
    ngrok_tunnel = ngrok.connect(PORT, bind_tls=True)
    WEBHOOK_URL = f"{ngrok_tunnel.public_url}/webhook"
    print(f"ngrok tunnel established: {WEBHOOK_URL}")
    
    repo, github_repo = init_repo(WEBHOOK_URL)
    
    handle_prompt("Add a login page", repo)
    handle_prompt("Fix the button styling", repo)
    
    print(f"Webhook server running at {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=PORT)