# AI Web Workflow Capturer

A generalizable system that accepts natural language tasks, automatically navigates live web apps with Playwright, detects significant UI states (including non-URL states like modals/forms), and captures step-by-step screenshots with metadata into a structured dataset.

## ✅ Status: Complete & Tested

Successfully captured **4 Notion workflows** with **19 screenshots** demonstrating:
- Database creation flows
- Page creation workflows  
- Filter functionality
- Linked database views

## Features
- ✅ AI-powered task planning (Anthropic/OpenAI) with robust heuristic fallback
- ✅ Playwright-based execution with persistent sessions & authentication
- ✅ Smart state detection (URL, DOM diffs, modal/overlay detection, loading states)
- ✅ Screenshot capture with comprehensive metadata per step
- ✅ Structured dataset per app/task with detailed workflow documentation
- ✅ Error-resilient execution (continues on failures, captures error states)
- ✅ Timeout protection on all actions (5-30s depending on operation)

## Project Structure
```
project/
  src/
    agent/
      task_planner.py
      action_executor.py
      state_detector.py
    capture/
      screenshot_manager.py
      metadata_handler.py
    config/
      app_configs.py
      credentials.py
    utils/
      browser_helpers.py
      ai_helpers.py
  dataset/
  main.py
  requirements.txt
  README.md
```

## Setup
1. Python 3.10+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   python -m playwright install
   ```
4. Copy `.env.example` to `.env` and fill values (optional). You can use `--manual-login` to log in once and reuse the profile.

## Usage
Run a task:
```bash
python main.py --app trello --task "Create a new board and add a list" --manual-login
```
Common flags:
- `--headless` (default false via .env)
- `--profile .playwright` persistent context dir
- `--out dataset` output root
- `--max-steps 20` limit actions

## Adding Apps
- Add baseline URLs and login endpoints in `src/config/app_configs.py`.
- Provide optional login helpers in `src/utils/browser_helpers.py`.
- No hardcoding of flows is required; the planner + executor adapt via selectors.

## Dataset Layout
```
dataset/
  trello/
    create-board/
      step-01-open.png
      step-02-modal-open.png
      step-03-form-filled.png
      metadata.json
    add-list/
      ...
  notion/
    create-database/
      ...
```
`metadata.json` contains steps with timestamps, URL, action, selectors used, and detection signals.

## Notes
- Start in headful mode for debugging; switch to headless as needed.
- Use `--manual-login` once; persistent profile will reuse sessions.
- If no API key is set, the heuristic planner will generate generic exploratory steps based on the task.
