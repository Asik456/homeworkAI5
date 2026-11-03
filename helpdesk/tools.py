import copy
import json
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HELPDESK = json.loads((DATA_DIR / "helpdesk.json").read_text(encoding="utf-8"))
STATUS = json.loads((DATA_DIR / "service_status.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((DATA_DIR / "ticket_template.json").read_text(encoding="utf-8"))["ticket"]


def ticket_folder():
    return Path(os.environ.get("TICKET_DIR", ROOT / "outputs" / "tickets"))


def normalise_topic(topic):
    text = str(topic).lower().strip()
    for name, aliases in HELPDESK["topic_aliases"].items():
        if text == name or text in aliases:
            return name
    return None


def find_instructions(topic):
    name = normalise_topic(topic)
    if name is None:
        return {"error": f"no instructions for '{topic}'", "known_topics": list(HELPDESK["instructions"])}
    guide = HELPDESK["instructions"][name]
    return {
        "instruction_id": guide["instruction_id"],
        "title": guide["title"],
        "steps": guide["steps"],
        "source": "data/helpdesk.json",
    }


def check_service_status(service, status_profile):
    topic = normalise_topic(service)
    service_name = HELPDESK["topic_services"][topic] if topic else str(service).lower().strip()
    if status_profile not in STATUS["profiles"]:
        return {"error": f"unknown status profile '{status_profile}'"}
    profile = STATUS["profiles"][status_profile]
    if service_name not in profile:
        return {"error": f"unknown service '{service}'", "known_services": list(profile)}
    entry = profile[service_name]
    return {
        "service": service_name,
        "status": entry["status"],
        "message": entry["message"],
        "status_profile": status_profile,
        "source": "data/service_status.json",
    }


def prepare_ticket(category, summary, steps_tried, service_status, user_id, thread_id, status_profile):
    if not str(summary).strip():
        return {"error": "missing problem description: ask the user what the problem is"}
    if not steps_tried:
        return {"error": "missing steps already tried: ask the user what they already tried"}

    topic = normalise_topic(category)
    ticket = copy.deepcopy(TEMPLATE)
    ticket["ticket_id"] = "TKT-" + uuid.uuid4().hex[:8].upper()
    ticket["user_id"] = user_id
    ticket["thread_id"] = thread_id
    ticket["category"] = topic or str(category)
    ticket["summary"] = str(summary).strip()
    ticket["steps_tried"] = [str(step) for step in steps_tried]
    ticket["service_status"] = service_status or "not checked"
    ticket["status_profile"] = status_profile
    ticket["reference_ids"] = [HELPDESK["instructions"][topic]["instruction_id"]] if topic else []

    folder = ticket_folder()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{ticket['ticket_id']}.json"
    path.write_text(json.dumps(ticket, indent=2, ensure_ascii=False), encoding="utf-8")
    shown = path.relative_to(ROOT) if ROOT in path.parents else path
    return {"ticket_id": ticket["ticket_id"], "file": str(shown), "status": "draft", "sent": False}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "find_instructions",
            "description": "Get the official troubleshooting steps for one topic from the local helpdesk guide. Topics: wifi, password. Always use this instead of writing steps from memory.",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string", "enum": ["wifi", "password"]}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_service_status",
            "description": "Check if a service is operational, has an outage, or has an unknown status. Use 'wifi' for Wi-Fi and 'password' for account recovery. 'unknown' means the status could not be checked: it is NOT operational and NOT a confirmed outage.",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string", "enum": ["wifi", "password"]}},
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_ticket",
            "description": "Save a LOCAL ticket draft (nothing is sent). Needs the problem description and the steps the user said they already tried. Use only facts from the conversation; never invent steps. Returns the ticket id and file name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["wifi", "password", "other"]},
                    "summary": {"type": "string", "description": "Short description of the problem in the user's words"},
                    "steps_tried": {"type": "array", "items": {"type": "string"}, "description": "Steps the user said they already tried"},
                    "service_status": {"type": "string", "description": "operational, outage, unknown, or 'not checked'"},
                },
                "required": ["category", "summary", "steps_tried", "service_status"],
            },
        },
    },
]


def run_tool(name, args, user_id, thread_id, status_profile):
    if not isinstance(args, dict):
        return {"error": "arguments must be an object"}
    try:
        if name == "find_instructions":
            return find_instructions(args["topic"])
        if name == "check_service_status":
            return check_service_status(args["service"], status_profile)
        if name == "prepare_ticket":
            return prepare_ticket(
                args["category"], args["summary"], args.get("steps_tried", []), args.get("service_status"),
                user_id, thread_id, status_profile,
            )
    except KeyError as missing:
        return {"error": f"missing argument {missing}"}
    return {"error": f"unknown tool '{name}'"}
