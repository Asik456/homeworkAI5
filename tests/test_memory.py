from langchain_core.messages import AIMessage

from helpdesk.app import Helpdesk
from helpdesk.fake_model import FakeModelForTests
from helpdesk.memory import find_language_request, get_language


def system_prompt_seen(model):
    return model.seen[-1][0].content


def test_conversation_survives_a_restart():
    first = Helpdesk(FakeModelForTests([AIMessage("noted")]))
    first.chat("My issue is Wi-Fi. I tried reconnecting.", "demo-user-a", "restart-a", "normal")
    first.close()

    second = Helpdesk(FakeModelForTests([AIMessage("You tried reconnecting.")]))
    saved = second.saved_messages("demo-user-a", "restart-a")
    second.close()

    assert [message.content for message in saved] == ["My issue is Wi-Fi. I tried reconnecting.", "noted"]


def test_model_sees_earlier_messages_in_the_same_thread():
    model = FakeModelForTests([AIMessage("ok"), AIMessage("You tried reconnecting.")])
    app = Helpdesk(model)
    app.chat("My Wi-Fi fails. I tried reconnecting.", "demo-user-a", "s10", "normal")
    app.chat("I already tried that.", "demo-user-a", "s10", "normal")
    app.close()

    contents = [message.content for message in model.seen[-1]]
    assert "My Wi-Fi fails. I tried reconnecting." in contents


def test_language_preference_is_found_in_a_message():
    assert find_language_request("Please remember that I prefer replies in Kazakh.") == "Kazakh"
    assert find_language_request("I have a Wi-Fi problem.") is None


def test_preference_is_shared_between_threads_of_the_same_user():
    first = Helpdesk(FakeModelForTests([AIMessage("ok")]))
    first.chat("Please remember that I prefer replies in Kazakh.", "demo-user-a", "preference-a1", "normal")
    first.close()

    model = FakeModelForTests([AIMessage("Kazakh")])
    second = Helpdesk(model)
    second.chat("Which language did I ask you to use?", "demo-user-a", "preference-a2", "normal")
    new_thread = second.saved_messages("demo-user-a", "preference-a2")
    second.close()

    assert get_language("demo-user-a") == "Kazakh"
    assert "replies in Kazakh" in system_prompt_seen(model)
    assert len(new_thread) == 2


def test_other_user_does_not_see_the_preference_or_conversation():
    app = Helpdesk(FakeModelForTests([AIMessage("ok")]))
    app.chat("Please remember that I prefer replies in Kazakh. I have a Wi-Fi problem.", "demo-user-a", "same-name", "normal")
    app.close()

    model = FakeModelForTests([AIMessage("Nothing is recorded.")])
    app = Helpdesk(model)
    app.chat("Have I told you a preferred language?", "demo-user-b", "same-name", "normal")
    other_user_messages = app.saved_messages("demo-user-b", "same-name")
    app.close()

    assert get_language("demo-user-b") is None
    assert "Kazakh" not in system_prompt_seen(model)
    assert all("Wi-Fi problem" not in message.content for message in other_user_messages)
