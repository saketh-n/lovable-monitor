# Lovable Monitor

A Python script to monitor manual changes in a Git repo synced with Lovable, collecting data for fine-tuning Lovable’s AI model. When a manual diff is pushed (not by the `lovable-bot`), it captures the added lines and pairs them with the prompt history.

## Purpose
This tool helps Lovable’s team improve the AI by identifying where it misunderstood prompts, using manual corrections as the “correct” output. The output is a lean JSON file with just the diffs and prompts.

## Setup

### Prerequisites
- Python 3.9+- Git installed
- A GitHub Personal Access Token with `repo` and `admin:repo_hook` scopes
- Sign up for `ngrok` and follow their setup instructions
- `ngrok` installed (in `/usr/local/bin/` or equivalent)

### Installation
1. **Clone the Repo**:
   ```bash
   git clone https://github.com/saketh-n/lovable-monitor.git
   cd lovable-monitor
   ```

2. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Set the Environment Variables**:
- Replace `<your_github_token>` with your GitHub Personal Access Token.
   ```bash
   export GITHUB_HOOK_TOKEN=<your_github_token>
   ```
- Add to `~/.zshrc` for persistence
```bash
echo "export GITHUB_HOOK_TOKEN=<your_github_token>" >> ~/.zshrc
source ~/.zshrc
```

## Usage
1. **Run the Script**:
   ```bash
   python3 lovable_monitor.py
   ```
   - Creates or uses `lovable-mock-repo` on GitHub.
   - Simulates Lovable prompts (`"Add a login page"`, `"Fix the button styling"`).
   - Starts a webhook server via `ngrok`

2. **Test a Manual Change**:
```bash
cd lovable-mock-repo
echo "Manual edit" >> prompts.txt
git add prompts.txt
git commit -m "Manual edit"
git push
```
- The webhook will trigger and save the manual diffs and prompt history to `fine_tune_data.json`.

3. Check Output:
- See `fine_tune_data.json` for the result, e.g:
```json
{"manual_diffs": [["Manual edit 3"]], "prompt_history": ["Add a login page", "Fix the button styling"]}
```

## Notes
- Only added lines from manual diffs are included, paired with all prompts from the time of the last manual change
- Webhook: Uses `ngrok` for a dynamic URL-each run will have a new one



