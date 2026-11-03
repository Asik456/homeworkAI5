from langchain_core.messages import AIMessage


class FakeModelForTests:
    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.seen.append(messages)
        if self.replies:
            return self.replies.pop(0)
        return AIMessage("fake model: no more scripted replies")


def tool_call(name, args, call_id):
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": call_id}])
