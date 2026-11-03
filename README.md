# HW5 — University IT helpdesk with LangGraph

A small terminal helpdesk. It answers Wi-Fi and password questions, checks a (fictional) service status, prepares **local** ticket drafts, and remembers the conversation and the user's language.
All data is invented. Nothing is sent to a real helpdesk.

The original assignment text is in [ASSIGNMENT.md](ASSIGNMENT.md). My answers and results are in [SUBMISSION.md](SUBMISSION.md).

## What is in this repository

| Path | What it does |
| --- | --- |
| `helpdesk/part1.py` | Part 1: graph **without a model**. Python rules choose the next node. |
| `helpdesk/tools.py` | Part 2: the three tools `find_instructions`, `check_service_status`, `prepare_ticket`. Each works alone. |
| `helpdesk/agent.py` | Part 2–3: the graph with the model, the tool loop and the round limit. |
| `helpdesk/memory.py` | Part 3: user memory (saved language) in a JSON file. |
| `helpdesk/app.py` | Part 3: connects the graph to the SQLite checkpointer and builds the trace. |
| `helpdesk/cli.py` | The terminal program. |
| `helpdesk/fake_model.py` | A **fake model used only in tests**. It returns scripted replies, so tests need no API key. |
| `run_scenarios.py` | Runs scenarios S01–S14 from `data/scenarios.json` and saves logs. |
| `tests/` | Tests for routing, tools, the tool loop and memory. |
| `outputs/logs/` | My saved runs (one JSON file per scenario). |
| `outputs/tickets/` | Ticket drafts created during my runs (invented data). |

## 1. Install

I used **Python 3.12.15**. LangGraph 1.x needs Python 3.10 or newer.

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt` has the exact versions of the packages I use (LangGraph 1.2.19). `requirements-lock.txt` has every installed package, if you want the identical environment.

## 2. Configure the model (only for Parts 2–3)

```bash
cp .env.example .env
```

Then put your key in `.env`. I used **OpenRouter** with the model `openai/gpt-5.6-luna` through the OpenAI adapter (`langchain-openai`):

```
OPENAI_API_KEY=<your OpenRouter key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=openai/gpt-5.6-luna
```

For OpenAI directly, leave `OPENAI_BASE_URL` empty and set an OpenAI model name. `.env` is ignored by git; never commit a key.

## 3. Run

**Part 1 (no key needed):**

```bash
python -m helpdesk.part1 "I cannot connect to Wi-Fi."
python -m helpdesk.part1 "My Wi-Fi password does not work."
python -m helpdesk.part1 "My Wi-Fi password does not work." --clarify
```

**Parts 2–3 — interactive chat:**

```bash
python -m helpdesk.cli --user demo-user-a --thread my-chat --status normal
```

- `--user` is the invented user id (`demo-user-a`, `demo-user-b`).
- `--thread` is the conversation id. Use the same thread again to continue a conversation.
- `--status` chooses the service-status snapshot: `normal`, `wifi_outage`, `recovery_outage`, `status_unavailable`.
- `--trace` prints the nodes, tool requests, tool results and memory sources.
- Type `quit` to close the program.

**Send messages without the interactive prompt:**

```bash
python -m helpdesk.cli --user demo-user-a --thread s10 -m "I cannot connect to Wi-Fi." -m "I already tried that." --trace
```

**Restart test by hand (same thread, new process):**

```bash
python -m helpdesk.cli --user demo-user-a --thread restart-a -m "Please remember that I prefer replies in Kazakh. My issue is Wi-Fi."
python -m helpdesk.cli --user demo-user-a --thread restart-a -m "Which problem did we discuss?" --trace
```

**All supplied scenarios (S01–S14):**

```bash
python run_scenarios.py            # all scenarios
python run_scenarios.py S06 S11    # only some
```

Each `restart_process` event really ends the Python process and starts a new one (the log shows a different `process_id`). Logs go to `outputs/logs/S01.json` … `S14.json`.

**The tools alone, without the model:**

```bash
python -m helpdesk.tools
```

## 4. Where memory is saved, and how to clear it

| What | Where | Key |
| --- | --- | --- |
| Conversation memory (LangGraph checkpointer) | `local-storage/checkpoints.sqlite` | `user_id/thread_id` |
| User memory (saved language) | `local-storage/users.json` | `user_id` |
| Ticket drafts | `outputs/tickets/TKT-xxxxxxxx.json` | ticket id |

The folder can be changed with `HELPDESK_STORAGE_DIR` in `.env`. `local-storage/` is ignored by git.

To start again from nothing:

```bash
rm -rf local-storage                                        # delete all saved conversations and preferences
python -m helpdesk.cli --reset --user demo-user-a --thread new   # or: --reset does the same before starting
```

`run_scenarios.py` clears `local-storage` itself before every scenario with `reset_before: true`.

## 5. Tests

```bash
python -m pytest -v
```

The tests need **no API key**. They use `FakeModelForTests` (in `helpdesk/fake_model.py`), which returns scripted replies instead of calling a real model. Each test uses its own temporary storage folder.

| Test file | What it checks | What it would catch |
| --- | --- | --- |
| `test_routing.py` | the four Part 1 messages, uppercase, the `clarify_problem` variant | a wrong routing rule, lost case-insensitivity, the clarification node not connected |
| `test_tools.py` | each tool alone: instructions, status for every snapshot, ticket file content, missing details | wrong data file, `unknown` treated as `operational`, a ticket saved without steps |
| `test_agent_loop.py` | tool result goes back to the model, the round limit, user/thread come from the app | a loop that never ends, tool results not returned, the model choosing whose data to use |
| `test_memory.py` | conversation after a restart (new connection to the same SQLite file), "that" refers to earlier messages, language shared between threads of one user, nothing shared with another user | lost memory after restart, mixed users, mixed threads |

The real-model runs (Part 2 and the scenarios) are separate and need the key.

## 6. GitHub Actions (CI)

`.github/workflows/tests.yml` runs `python -m pytest -v` on every push, on Ubuntu with Python 3.12. It uses only the fake model, so it needs no secrets.
