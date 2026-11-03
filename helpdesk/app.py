import json
import sqlite3

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from helpdesk.agent import build_agent
from helpdesk.memory import storage_dir


class Helpdesk:
    def __init__(self, model):
        self.connection = sqlite3.connect(storage_dir() / "checkpoints.sqlite", check_same_thread=False)
        self.graph = build_agent(model, SqliteSaver(self.connection))

    def close(self):
        self.connection.close()

    def config(self, user_id, thread_id):
        return {"configurable": {"thread_id": f"{user_id}/{thread_id}"}}

    def saved_messages(self, user_id, thread_id):
        state = self.graph.get_state(self.config(user_id, thread_id))
        return state.values.get("messages", [])

    def chat(self, message, user_id, thread_id, status_profile):
        earlier = len(self.saved_messages(user_id, thread_id))
        start = {"messages": [HumanMessage(message)], "user_id": user_id, "thread_id": thread_id, "status_profile": status_profile}
        trace = []
        tools_used = []
        reply = ""
        limit_reached = False
        for step in self.graph.stream(start, self.config(user_id, thread_id), stream_mode="updates"):
            for node, update in step.items():
                update = update or {}
                entry = {"node": node}
                if node == "load_user_memory":
                    entry["user_memory_language"] = update.get("language")
                    entry["language_saved_now"] = update.get("language_saved_now")
                for item in update.get("messages", []):
                    if item.type == "ai" and item.tool_calls:
                        entry.setdefault("tool_requests", []).extend(
                            {"tool": call["name"], "args": call["args"]} for call in item.tool_calls
                        )
                    elif item.type == "ai":
                        entry["answer"] = item.content
                        reply = item.content
                    elif item.type == "tool":
                        result = json.loads(item.content)
                        entry.setdefault("tool_results", []).append({"tool": item.name, "result": result})
                        tools_used.append((item.name, result))
                if "tool_rounds" in update and node == "tools":
                    entry["tool_rounds"] = update["tool_rounds"]
                if node == "limit_reached":
                    limit_reached = True
                trace.append(entry)

        language = next((step.get("user_memory_language") for step in trace if step["node"] == "load_user_memory"), None)
        sources = {
            "conversation_memory": f"{earlier} earlier messages loaded from the checkpoint for thread '{thread_id}'",
            "user_memory": f"language = {language}" if language else "no saved preference for this user",
            "reference_file": sorted({"data/helpdesk.json" for name, _ in tools_used if name == "find_instructions"}
                                     | {"data/service_status.json" for name, _ in tools_used if name == "check_service_status"}),
        }
        tickets = [result["file"] for name, result in tools_used if name == "prepare_ticket" and "file" in result]
        return {
            "reply": reply,
            "trace": trace,
            "sources": sources,
            "ticket_files": tickets,
            "loop_limit_reached": limit_reached,
        }
