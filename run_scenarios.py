import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpdesk.memory import reset_storage
from helpdesk.part1 import run as run_part1

ROOT = Path(__file__).resolve().parent
SCENARIOS = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]
LOGS = ROOT / "outputs" / "logs"


def find_scenario(scenario_id):
    return next(item for item in SCENARIOS if item["id"] == scenario_id)


def split_at_restarts(events):
    segments = [[]]
    for event in events:
        if event["action"] == "restart_process":
            segments.append([])
        else:
            segments[-1].append(event)
    return segments


def run_segment(scenario_id, index):
    load_dotenv(ROOT / ".env")
    from helpdesk.agent import real_model
    from helpdesk.app import Helpdesk

    scenario = find_scenario(scenario_id)
    events = split_at_restarts(scenario["events"])[index]
    app = Helpdesk(real_model())
    results = []
    for event in events:
        result = app.chat(event["message"], event["user_id"], event["thread_id"], scenario["status_profile"])
        results.append({"user_id": event["user_id"], "thread_id": event["thread_id"], "message": event["message"],
                        "process_id": os.getpid(), **result})
    app.close()
    print(json.dumps(results, ensure_ascii=False))


def run_scenario(scenario):
    log = {
        "scenario": scenario["id"],
        "title": scenario["title"],
        "part": scenario["part"],
        "status_profile": scenario["status_profile"],
        "command": f"python run_scenarios.py {scenario['id']}",
        "reset_before": scenario["reset_before"],
        "events": [],
    }
    if scenario["reset_before"]:
        reset_storage()

    if scenario["part"] == 1:
        with_clarification = scenario.get("graph_variant") == "with_clarification"
        log["graph_variant"] = "with_clarification" if with_clarification else "original"
        for event in scenario["events"]:
            state, trace = run_part1(event["message"], with_clarification)
            log["events"].append({"user_id": event["user_id"], "thread_id": event["thread_id"], "message": event["message"],
                                  "route": ["START"] + [step["node"] for step in trace] + ["END"],
                                  "trace": trace, "reply": state["reply"]})
    else:
        for index, _ in enumerate(split_at_restarts(scenario["events"])):
            if index > 0:
                log["events"].append({"action": "restart_process",
                                      "note": "the previous Python process ended; a new process starts with the same local-storage"})
            finished = subprocess.run([sys.executable, str(Path(__file__)), "--segment", scenario["id"], str(index)],
                                      capture_output=True, text=True, cwd=ROOT)
            if finished.returncode != 0:
                raise RuntimeError(finished.stderr)
            log["events"].extend(json.loads(finished.stdout.strip().splitlines()[-1]))

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"{scenario['id']}.json").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    return log


def main():
    if sys.argv[1:2] == ["--segment"]:
        run_segment(sys.argv[2], int(sys.argv[3]))
        return
    chosen = sys.argv[1:] or [item["id"] for item in SCENARIOS]
    for scenario_id in chosen:
        log = run_scenario(find_scenario(scenario_id))
        print(f"===== {log['scenario']} {log['title']} (status: {log['status_profile']})")
        for event in log["events"]:
            if event.get("action") == "restart_process":
                print("   --- restart_process ---")
                continue
            print(f"   [{event['user_id']} / {event['thread_id']}] {event['message']}")
            if "route" in event:
                print("   route:", " -> ".join(event["route"]))
            for step in event.get("trace", []):
                for request in step.get("tool_requests", []):
                    print(f"   tool request: {request['tool']}({json.dumps(request['args'], ensure_ascii=False)})")
            print("   reply:", event["reply"][:300].replace("\n", " "))
            for path in event.get("ticket_files", []):
                print("   ticket:", path)


if __name__ == "__main__":
    main()
