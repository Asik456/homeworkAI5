import json
import os

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from helpdesk.tools import TOOL_SCHEMAS, run_tool

MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """You are a university IT helpdesk assistant. This is a practice version: all data is fictional and local.
You help only with: Wi-Fi troubleshooting, password recovery guidance, service status lookup, and preparing local ticket drafts.

Rules:
- For instructions, call find_instructions. Never write troubleshooting steps from memory.
- When the user asks whether a service is down, call check_service_status.
- Follow the user's conditions exactly. Example: "if it is operating, prepare a ticket" means:
  status operational -> prepare the ticket; status outage -> do NOT prepare it, explain why;
  status unknown -> do NOT prepare it, say you cannot confirm the status and ask if they want a draft that says the status could not be checked.
- prepare_ticket needs the problem description and the steps the user already tried. If they are missing, ask the user. Never invent steps, repair times or outages.
- A ticket is only a local draft. Say that nothing was sent and give the ticket file name.
- Never ask for or store passwords, API keys or recovery codes.
- Use the earlier messages of this conversation to understand words like "that" or "the steps we discussed".
"""


class AgentState(MessagesState):
    user_id: str
    thread_id: str
    status_profile: str
    tool_rounds: int


def start_turn(state):
    return {"tool_rounds": 0}


def make_agent_node(model):
    model_with_tools = model.bind_tools(TOOL_SCHEMAS)

    def agent(state):
        messages = [SystemMessage(SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [model_with_tools.invoke(messages)]}

    return agent


def tools(state):
    last = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        result = run_tool(call["name"], call["args"], state["user_id"], state["thread_id"], state["status_profile"])
        results.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"], name=call["name"]))
    return {"messages": results, "tool_rounds": state["tool_rounds"] + 1}


def limit_reached(state):
    last = state["messages"][-1]
    skipped = [
        ToolMessage(content=json.dumps({"error": "not run: tool limit reached"}), tool_call_id=call["id"], name=call["name"])
        for call in last.tool_calls
    ]
    stop = AIMessage(f"I stopped because I reached the limit of {MAX_TOOL_ROUNDS} tool rounds. Please rephrase or give more details.")
    return {"messages": skipped + [stop]}


def route_after_agent(state):
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return "limit_reached"
    return "tools"


def build_agent(model, checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("start_turn", start_turn)
    graph.add_node("agent", make_agent_node(model))
    graph.add_node("tools", tools)
    graph.add_node("limit_reached", limit_reached)

    graph.add_edge(START, "start_turn")
    graph.add_edge("start_turn", "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["tools", "limit_reached", END])
    graph.add_edge("tools", "agent")
    graph.add_edge("limit_reached", END)
    return graph.compile(checkpointer=checkpointer)


def real_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
        use_responses_api=False,
        extra_body={"provider": {"allow_fallbacks": False}} if os.environ.get("OPENAI_BASE_URL") else None,
    )
