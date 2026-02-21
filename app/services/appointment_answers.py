from dotenv import load_dotenv
import json
import os
import requests


load_dotenv()

AIRIA_API_KEY = os.getenv("AIRIA_API_KEY") or os.getenv("api_key")
AIRIA_PIPELINE_URL = os.getenv(
    "AIRIA_PIPELINE_URL",
    "https://api.airia.ai/v2/PipelineExecution/e08e0c25-8b5a-48db-b007-907fc9dc5dc2",
)

DEFAULT_IMPROVEMENT_RULES = """
- Do not assume appointment availability.
- Always confirm date and time before finalizing booking.
- If the user changes their request, discard previous booking attempts.
- Keep responses under 5 sentences unless clarification is needed.
- Do not fabricate policies or business hours.
""".strip()


def generate_summary(previous_messages, state):
    """
    Generate summary once per turn.
    If already generated for this turn, return existing summary.
    """
    if state.get("summary_generated", False):
        return state.get("conversation_summary", "No prior context.")

    recent = previous_messages[-12:]
    if not recent:
        summary = "No prior context."
    else:
        lines = []
        for msg in recent:
            role = msg.get("role", "unknown").capitalize()
            content = " ".join(str(msg.get("content", "")).split())
            if len(content) > 220:
                content = content[:220] + "..."
            lines.append(f"- {role}: {content}")
        summary = "Conversation summary:\n" + "\n".join(lines)

    state["conversation_summary"] = summary
    state["summary_generated"] = True
    return summary


def build_user_prompt(conversation_summary, transcript_input, improvement_rules=DEFAULT_IMPROVEMENT_RULES):
    return f"""
You are continuing an ongoing conversation.

CONVERSATION SUMMARY:
{conversation_summary}

IMPORTANT IMPROVEMENT RULES:
{improvement_rules}

CURRENT USER MESSAGE:
{transcript_input}

Instructions:
1. Use the conversation summary to maintain context.
2. Do not repeat past information unnecessarily.
3. Only use relevant details from the summary.
4. If key details are missing, ask a focused clarification question.
5. Follow the improvement rules strictly.
6. Respond naturally and clearly.

Return only the final assistant response.
""".strip()


def build_payload(user_prompt, system_prompt=""):
    return {
        "variables": {
            "systemPrompt": system_prompt,
        },
        "userInput": user_prompt,
        "asyncOutput": False,
    }


def call_airia(payload, api_key=AIRIA_API_KEY, pipeline_url=AIRIA_PIPELINE_URL, timeout=30):
    if not api_key:
        raise ValueError("AIRIA_API_KEY (or api_key) environment variable not set")
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    response = requests.post(pipeline_url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return response


def extract_assistant_output(response_json):
    if isinstance(response_json, str):
        return response_json
    if isinstance(response_json, dict):
        return (
            response_json.get("output")
            or response_json.get("result")
            or response_json.get("message")
            or response_json.get("output_text")
            or json.dumps(response_json)
        )
    return str(response_json)


def run_single_turn(transcript_input, previous_messages=None, conversation_state=None, system_prompt=""):
    if previous_messages is None:
        previous_messages = []
    if conversation_state is None:
        conversation_state = {"summary_generated": False, "conversation_summary": "No prior context."}

    # Read summary once for this turn.
    conversation_state["summary_generated"] = False
    conversation_summary = generate_summary(previous_messages, conversation_state)
    user_prompt = build_user_prompt(conversation_summary, transcript_input)
    payload = build_payload(user_prompt, system_prompt=system_prompt)

    response = call_airia(payload)
    response_json = response.json()
    assistant_output = extract_assistant_output(response_json)

    # Update conversation and summary once after assistant responds.
    previous_messages.append({"role": "user", "content": transcript_input})
    previous_messages.append({"role": "assistant", "content": assistant_output})
    conversation_state["summary_generated"] = False
    updated_summary = generate_summary(previous_messages, conversation_state)

    return {
        "status_code": response.status_code,
        "assistant_output": assistant_output,
        "updated_summary": updated_summary,
        "response_json": response_json,
        "previous_messages": previous_messages,
        "conversation_state": conversation_state,
    }


def main():
    sample_messages = []
    sample_state = {"summary_generated": False, "conversation_summary": "No prior context."}
    sample_transcript = "Hi, I want to book a dentist appointment for next week. Can you help me with that?"

    try:
        result = run_single_turn(
            transcript_input=sample_transcript,
            previous_messages=sample_messages,
            conversation_state=sample_state,
            system_prompt="",
        )
        print("Status Code:", result["status_code"])
        print("\nAssistant Output:\n", result["assistant_output"])
        print("\nUpdated Conversation Summary:\n", result["updated_summary"])
    except requests.exceptions.RequestException as exc:
        print("Request failed:", str(exc))


if __name__ == "__main__":
    main()
