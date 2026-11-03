from helpdesk.part1 import run


def route(message, with_clarification=False):
    state, trace = run(message, with_clarification)
    return [step["node"] for step in trace], state


def test_wifi_message_goes_to_wifi_help():
    nodes, state = route("I cannot connect to Wi-Fi.")
    assert nodes == ["read_request", "wifi_help"]
    assert state["category"] == "wifi"
    assert "GUIDE-WIFI" in state["reply"]


def test_uppercase_password_goes_to_password_help():
    nodes, state = route("I forgot my PASSWORD.")
    assert nodes == ["read_request", "password_help"]
    assert "GUIDE-PASSWORD" in state["reply"]


def test_other_message_asks_which_problem():
    nodes, state = route("My laptop screen is broken.")
    assert nodes == ["read_request", "other_help"]
    assert "Wi-Fi" in state["reply"] and "password" in state["reply"]


def test_both_topics_original_graph_takes_wifi_first():
    nodes, _ = route("My Wi-Fi password does not work.")
    assert nodes == ["read_request", "wifi_help"]


def test_both_topics_changed_graph_asks_to_clarify():
    nodes, state = route("My Wi-Fi password does not work.", with_clarification=True)
    assert nodes == ["read_request", "clarify_problem"]
    assert state["category"] == "both"


def test_state_keeps_original_message():
    _, state = route("I cannot connect to Wi-Fi.")
    assert state["message"] == "I cannot connect to Wi-Fi."
