import json
from pathlib import Path

from helpdesk.tools import check_service_status, find_instructions, prepare_ticket, run_tool


def test_find_instructions_wifi_and_alias():
    assert find_instructions("wifi")["instruction_id"] == "GUIDE-WIFI"
    assert find_instructions("Wi-Fi")["instruction_id"] == "GUIDE-WIFI"


def test_find_instructions_password_and_unknown():
    assert find_instructions("password")["instruction_id"] == "GUIDE-PASSWORD"
    assert "error" in find_instructions("printer")


def test_status_follows_selected_snapshot():
    assert check_service_status("wifi", "normal")["status"] == "operational"
    assert check_service_status("wifi", "wifi_outage")["status"] == "outage"
    assert check_service_status("wifi", "status_unavailable")["status"] == "unknown"


def test_password_uses_account_recovery_service():
    result = check_service_status("password", "recovery_outage")
    assert result["service"] == "account_recovery"
    assert result["status"] == "outage"


def test_status_unknown_profile_is_an_error():
    assert "error" in check_service_status("wifi", "not-a-profile")


def test_prepare_ticket_saves_local_draft(separate_storage):
    result = prepare_ticket("wifi", "Campus-Demo will not connect", ["enabled Wi-Fi", "forgot the network"],
                            "operational", "demo-user-a", "s06", "normal")
    assert result["sent"] is False
    saved = json.loads(Path(separate_storage / "tickets" / f"{result['ticket_id']}.json").read_text())
    assert saved["status"] == "draft"
    assert saved["user_id"] == "demo-user-a"
    assert saved["steps_tried"] == ["enabled Wi-Fi", "forgot the network"]
    assert saved["reference_ids"] == ["GUIDE-WIFI"]


def test_prepare_ticket_refuses_missing_details():
    assert "error" in prepare_ticket("wifi", "", ["tried"], None, "a", "t", "normal")
    assert "error" in prepare_ticket("wifi", "no connection", [], None, "a", "t", "normal")


def test_run_tool_rejects_unknown_tool_and_missing_arguments():
    assert "error" in run_tool("delete_everything", {}, "a", "t", "normal")
    assert "error" in run_tool("find_instructions", {}, "a", "t", "normal")
