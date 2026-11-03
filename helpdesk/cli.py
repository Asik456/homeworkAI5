import argparse
import json

from dotenv import load_dotenv

from helpdesk.agent import real_model
from helpdesk.app import Helpdesk
from helpdesk.memory import reset_storage


def show(result, verbose):
    if verbose:
        print(json.dumps({key: result[key] for key in ("trace", "sources")}, indent=2, ensure_ascii=False))
    print("helpdesk>", result["reply"])
    for path in result["ticket_files"]:
        print("ticket draft saved:", path)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="University IT helpdesk (practice version)")
    parser.add_argument("--user", required=True, help="invented user id, for example demo-user-a")
    parser.add_argument("--thread", required=True, help="conversation id, for example s10")
    parser.add_argument("--status", default="normal", choices=["normal", "wifi_outage", "recovery_outage", "status_unavailable"])
    parser.add_argument("-m", "--message", action="append", help="send this message and exit (can repeat)")
    parser.add_argument("--trace", action="store_true", help="print nodes, tool calls and memory sources")
    parser.add_argument("--reset", action="store_true", help="delete all saved conversations and preferences first")
    args = parser.parse_args()

    if args.reset:
        reset_storage()
    app = Helpdesk(real_model())
    try:
        if args.message:
            for message in args.message:
                print("you>", message)
                show(app.chat(message, args.user, args.thread, args.status), args.trace)
            return
        print(f"user={args.user} thread={args.thread} status={args.status}. Type 'quit' to exit.")
        while True:
            message = input("you> ").strip()
            if message in ("quit", "exit"):
                break
            if message:
                show(app.chat(message, args.user, args.thread, args.status), args.trace)
    finally:
        app.close()


if __name__ == "__main__":
    main()
