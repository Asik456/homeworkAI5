import json

from langchain_core.messages import AIMessage

from helpdesk.agent import MAX_TOOL_ROUNDS
from helpdesk.app import Helpdesk
from helpdesk.fake_model import FakeModelForTests, tool_call


def test_tool_result_goes_back_to_the_model():
    model = FakeModelForTests([tool_call("check_service_status", {"service": "wifi"}, "c1"), AIMessage("Wi-Fi is down.")])
    app = Helpdesk(model)
    result = app.chat("Is Wi-Fi down?", "demo-user-a", "t1", "wifi_outage")
    app.close()

    second_call = model.seen[1]
    tool_message = second_call[-1]
    assert tool_message.type == "tool"
    assert json.loads(tool_message.content)["status"] == "outage"
    assert result["reply"] == "Wi-Fi is down."
    assert [step["node"] for step in result["trace"]] == ["load_user_memory", "agent", "tools", "agent"]


def test_loop_stops_at_the_round_limit():
    endless = [tool_call("find_instructions", {"topic": "wifi"}, f"c{i}") for i in range(20)]
    app = Helpdesk(FakeModelForTests(endless))
    result = app.chat("loop forever", "demo-user-a", "t2", "normal")
    app.close()

    assert result["loop_limit_reached"] is True
    assert sum(1 for step in result["trace"] if step["node"] == "tools") == MAX_TOOL_ROUNDS


def test_ticket_tool_gets_user_and_thread_from_the_app_not_the_model(separate_storage):
    args = {"category": "wifi", "summary": "no connection", "steps_tried": ["reconnected"], "service_status": "operational"}
    app = Helpdesk(FakeModelForTests([tool_call("prepare_ticket", args, "c1"), AIMessage("Draft saved.")]))
    result = app.chat("make a ticket", "demo-user-a", "s09", "normal")
    app.close()

    ticket_id = result["trace"][2]["tool_results"][0]["result"]["ticket_id"]
    saved = json.loads((separate_storage / "tickets" / f"{ticket_id}.json").read_text())
    assert saved["user_id"] == "demo-user-a"
    assert saved["thread_id"] == "s09"
