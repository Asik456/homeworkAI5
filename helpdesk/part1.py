import argparse
import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HELPDESK = json.loads((DATA_DIR / "helpdesk.json").read_text(encoding="utf-8"))


class HelpState(TypedDict, total=False):
    message: str
    category: str
    reply: str


def has_topic(message, topic):
    text = message.lower()
    return any(alias in text for alias in HELPDESK["topic_aliases"][topic])


def find_category(message, with_clarification):
    wifi = has_topic(message, "wifi")
    password = has_topic(message, "password")
    if with_clarification and wifi and password:
        return "both"
    if wifi:
        return "wifi"
    if password:
        return "password"
    return "other"


def instructions_text(topic):
    guide = HELPDESK["instructions"][topic]
    steps = " ".join(f"{number}. {step}" for number, step in enumerate(guide["steps"], 1))
    return f"{guide['title']} ({guide['instruction_id']}): {steps}"


def read_request(state):
    return {"category": find_category(state["message"], with_clarification=False)}


def read_request_with_clarification(state):
    return {"category": find_category(state["message"], with_clarification=True)}


def choose_next(state):
    routes = {
        "wifi": "wifi_help",
        "password": "password_help",
        "both": "clarify_problem",
        "other": "other_help",
    }
    return routes[state["category"]]


def wifi_help(state):
    return {"reply": instructions_text("wifi")}


def password_help(state):
    return {"reply": instructions_text("password")}


def other_help(state):
    return {"reply": "I can help with Wi-Fi or password problems. Is your problem about Wi-Fi or about a password?"}


def clarify_problem(state):
    return {"reply": "Your message mentions both Wi-Fi and a password. Is the problem connecting to Wi-Fi, or recovering your account password?"}


def build_graph(with_clarification=False):
    graph = StateGraph(HelpState)
    if with_clarification:
        graph.add_node("read_request", read_request_with_clarification)
    else:
        graph.add_node("read_request", read_request)
    graph.add_node("wifi_help", wifi_help)
    graph.add_node("password_help", password_help)
    graph.add_node("other_help", other_help)
    targets = ["wifi_help", "password_help", "other_help"]
    if with_clarification:
        graph.add_node("clarify_problem", clarify_problem)
        targets.append("clarify_problem")

    graph.add_edge(START, "read_request")
    graph.add_conditional_edges("read_request", choose_next, targets)
    for target in targets:
        graph.add_edge(target, END)
    return graph.compile()


def run(message, with_clarification=False):
    graph = build_graph(with_clarification)
    state = {"message": message}
    trace = []
    for step in graph.stream({"message": message}, stream_mode="updates"):
        for node, update in step.items():
            state = {**state, **update}
            trace.append({"node": node, "update": update, "state_after": dict(state)})
    return state, trace


def main():
    parser = argparse.ArgumentParser(description="Part 1 helpdesk graph without a model")
    parser.add_argument("message")
    parser.add_argument("--clarify", action="store_true", help="use the graph with the clarify_problem node")
    args = parser.parse_args()

    state, trace = run(args.message, args.clarify)
    print("route: START -> " + " -> ".join(step["node"] for step in trace) + " -> END")
    for step in trace:
        print(f"[{step['node']}] update: {json.dumps(step['update'], ensure_ascii=False)}")
    print("reply:", state["reply"])


if __name__ == "__main__":
    main()
