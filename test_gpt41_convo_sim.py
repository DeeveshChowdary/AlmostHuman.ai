import requests

from test_gpt41 import generate_summary, run_single_turn


def import_voice_loop_session(session_id, previous_messages, conversation_state):
    url = f"http://127.0.0.1:8000/api/v1/voice-loop/sessions/{session_id}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()

    turns = payload.get("session", {}).get("turns", [])
    for turn in turns:
        user_text = turn.get("user_text")
        agent_text = turn.get("agent_text")
        if user_text:
            previous_messages.append({"role": "user", "content": user_text})
        if agent_text:
            previous_messages.append({"role": "assistant", "content": agent_text})

    conversation_state["summary_generated"] = False
    generate_summary(previous_messages, conversation_state)
    return len(turns)


def simulate_terminal_conversation():
    print("Conversation simulator started.")
    print("Type '/end' (or 'exit'/'quit') to stop.")
    print("Type '/summary' to print summary.")
    print("Type '/import <session_id>' to load turns from /voice-loop session.\n")

    previous_messages = []
    conversation_state = {
        "summary_generated": False,
        "conversation_summary": "No prior context.",
    }

    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue

        if user_text.lower() in {"/end", "exit", "quit"}:
            print("\nConversation ended.")
            print("\nFinal conversation summary:\n")
            print(conversation_state.get("conversation_summary", "No prior context."))
            break

        if user_text.lower() == "/summary":
            print("\nCurrent conversation summary:\n")
            print(conversation_state.get("conversation_summary", "No prior context."))
            print("")
            continue

        if user_text.startswith("/import "):
            session_id = user_text.replace("/import ", "", 1).strip()
            if not session_id:
                print("Assistant: Please provide a session id after /import.\n")
                continue
            try:
                turn_count = import_voice_loop_session(session_id, previous_messages, conversation_state)
                print(f"Assistant: Imported {turn_count} turns from session {session_id}.\n")
            except requests.exceptions.RequestException as exc:
                print(f"Assistant: Failed to import session: {exc}\n")
            continue

        try:
            result = run_single_turn(
                transcript_input=user_text,
                previous_messages=previous_messages,
                conversation_state=conversation_state,
                system_prompt="",
            )
            print(f"Assistant: {result['assistant_output']}\n")
        except requests.exceptions.RequestException as exc:
            print(f"Assistant: Request failed: {exc}\n")


if __name__ == "__main__":
    simulate_terminal_conversation()
