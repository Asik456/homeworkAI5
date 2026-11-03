# HW5 — My LangGraph helpdesk

**Name:** Askar Zhurabekov · **Student ID:** 67529 · **Group:** 9
**Repository:** https://github.com/Asik456/homeworkAI5

**AI assistance:** I used Claude Code (Anthropic) to help me plan the graphs, write the code and tests, run the scenarios and write this file from my own runs.

## Part 1 — How the graph works

### My graph and state

The first graph has **no model**. My own Python rules choose the path.

```mermaid
graph TD
    START([START]) --> read_request
    read_request -.->|category = wifi| wifi_help
    read_request -.->|category = password| password_help
    read_request -.->|category = other| other_help
    wifi_help --> END([END])
    password_help --> END
    other_help --> END
```

The state is one small dictionary:

| Field | What it holds | Who writes it |
| --- | --- | --- |
| `message` | the user's original message | the user (input) |
| `category` | `wifi`, `password` or `other` | `read_request` |
| `reply` | the answer for the user | one help node |

Example: input `{"message": "I cannot connect to Wi-Fi."}` → after `read_request`: `category = "wifi"` → after `wifi_help`: `reply = "Connect to the practice campus network (GUIDE-WIFI): 1. Check that Wi-Fi is enabled ..."`.

**1. What does each node read and change?**

| Node | Reads | Changes |
| --- | --- | --- |
| `read_request` | `message` | `category` |
| `wifi_help` | nothing from the state (it always gives the Wi-Fi guide from `data/helpdesk.json`) | `reply` |
| `password_help` | nothing from the state (password guide) | `reply` |
| `other_help` | nothing | `reply` (a question: Wi-Fi or password?) |

**2. A node update vs a conditional edge.** A node is a function that **returns the fields it wants to change**, for example `{"category": "wifi"}`. LangGraph merges this into the state. A conditional edge is a function that **only reads the state and returns the name of the next node** (for example `"wifi_help"`). It changes nothing in the state.

**3. What does the next node receive?** The **whole current state**, not only the last update. After `read_request`, `wifi_help` receives `message` and `category` together, because LangGraph merged the update into the state.

**4. START, END and compiling.** `START` is where the graph begins: the first node after it is `read_request`. `END` means "stop and return the final state". `compile()` checks the graph (all nodes and edges exist) and turns it into a program I can run with `invoke()` or `stream()`.

### Predictions before running

My rules check Wi-Fi first, then password, in lowercase.

| Message | Predicted route | Actual route | What I learned |
| --- | --- | --- | --- |
| I cannot connect to Wi-Fi. | read_request → wifi_help | | |
| I forgot my PASSWORD. | read_request → password_help (lowercase makes PASSWORD = password) | | |
| My laptop screen is broken. | read_request → other_help | | |
| My Wi-Fi password does not work. | read_request → wifi_help (Wi-Fi is checked first, so the password part is ignored) | | |

### My change to the graph

TODO

## Part 2 — Model and tools

TODO

## Part 3 — Memory

TODO

| Situation | Command used | Log file | What happened |
| --- | --- | --- | --- |
| Refer to an earlier message | | | |
| Close, restart and resume | | | |
| Same user, new conversation | | | |
| Different user | | | |

## Part 4 — Running and checking my work

TODO

## Choices and limitations

TODO

## Supplied scenarios — my actual results

| Scenario | Command or manual steps | Log file | What happened / what I changed |
| --- | --- | --- | --- |
| S01 — Simple Wi-Fi route | | | |
| S02 — Case-insensitive password route | | | |
| S03 — Unsupported request | | | |
| S04 — Two topics before the graph change | | | |
| S05 — Two topics after adding clarification | | | |
| S06 — Instructions then local ticket | | | |
| S07 — The same request during a Wi-Fi outage | | | |
| S08 — Status source unavailable | | | |
| S09 — Missing ticket details | | | |
| S10 — Use the current conversation | | | |
| S11 — Persist and recall after restart | | | |
| S12 — Preference across threads without replay | | | |
| S13 — Do not share memory between users | | | |
| S14 — Password recovery outage | | | |
