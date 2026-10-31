#!/usr/bin/env python3
"""
Antigravity Ambient Lighting Lifecycle Hook Handler
Receives hook events on stdin, controls room lamp accordingly, and outputs JSON contract on stdout.
"""

import sys
import json
import subprocess

def run_wiz(signal_type):
    try:
        subprocess.run(["/Users/yashdeepraj/.local/bin/wiz", "signal", signal_type], capture_output=True, timeout=1.0)
    except Exception:
        pass

def main():
    event = sys.argv[1] if len(sys.argv) > 1 else ""

    # Parse stdin input if available
    payload = {}
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            if content.strip():
                payload = json.loads(content)
    except Exception:
        pass

    if event == "pre_tool":
        tool_name = payload.get("toolCall", {}).get("name", "")
        # For ask_question or run_command which may require user confirmation:
        if tool_name in ("ask_question", "run_command"):
            run_wiz("blue")
        print(json.dumps({"decision": "allow"}))

    elif event == "post_tool":
        tool_name = payload.get("toolCall", {}).get("name", "")
        if payload.get("error"):
            run_wiz("red")
        else:
            run_wiz("warm")
        print(json.dumps({}))

    elif event == "stop":
        err = payload.get("error")
        if err:
            run_wiz("red")
        else:
            run_wiz("green")
        print(json.dumps({"decision": "continue" if False else "stop"}))

    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
