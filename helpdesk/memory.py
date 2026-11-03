import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PREFERENCE_PATTERN = re.compile(r"prefer (?:replies|answers|responses) in ([A-Za-z]+)", re.IGNORECASE)


def storage_dir():
    folder = Path(os.environ.get("HELPDESK_STORAGE_DIR", "local-storage"))
    if not folder.is_absolute():
        folder = ROOT / folder
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def reset_storage():
    shutil.rmtree(storage_dir(), ignore_errors=True)
    storage_dir()


def users_file():
    return storage_dir() / "users.json"


def load_users():
    path = users_file()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_language(user_id):
    return load_users().get(user_id, {}).get("language")


def save_language(user_id, language):
    users = load_users()
    users.setdefault(user_id, {})["language"] = language
    users_file().write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


def find_language_request(message):
    found = PREFERENCE_PATTERN.search(message)
    if found:
        return found.group(1).capitalize()
    return None
