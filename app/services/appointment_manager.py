import os
import json
import aiohttp
from app.utils.gemini_analyzer import generate_insights_from_transcript
from app.core.config import settings

DEFAULT_IMPROVEMENT_RULES = """
- Do not assume appointment availability.
- Always confirm date and time before finalizing booking.
- If the user changes their request, discard previous booking attempts.
- Keep responses under 5 sentences unless clarification is needed.
- Do not fabricate policies or business hours.
""".strip()

class AppointmentManager:
    """
    Core service for managing appointments and handling the AI improvement loop 
    using Google's latest model (e.g., Gemini 3) via the Airia Pipeline.
    """
    def __init__(self):
        self.rules_file = "app/data/rules.json"
        self.airia_answers_pipeline_url = os.getenv(
            "AIRIA_PIPELINE_URL",
            "https://api.airia.ai/v2/PipelineExecution/e08e0c25-8b5a-48db-b007-907fc9dc5dc2"
        )
        self.api_key = settings.AIRIA_API_KEY

    def load_rules(self) -> list[str]:
        if not os.path.exists(self.rules_file):
            print("ERROR! RULES FILE NOT FOUND")
            return [
                rule.strip("- ").strip() 
                for rule in DEFAULT_IMPROVEMENT_RULES.split("\n") 
                if rule.strip()
            ]
        try:
            with open(self.rules_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_rules(self, rules: list[str]):
        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        with open(self.rules_file, "w") as f:
            json.dump(rules, f, indent=4)
            
    def generate_summary(self, previous_messages, state):
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
        
    def build_user_prompt(self, conversation_summary, transcript_input, improvement_rules):
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

    @staticmethod
    def _extract_response_text(content):
        if isinstance(content, dict):
            return str(content.get("response", content))
        if isinstance(content, str):
            stripped = content.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    payload = json.loads(stripped)
                    if isinstance(payload, dict) and "response" in payload:
                        return str(payload["response"])
                except json.JSONDecodeError:
                    pass
            return stripped
        return str(content)

    def messages_as_turn_json(self, previous_messages: list[dict]) -> dict:
        turns = []
        current_user = None
        for msg in previous_messages:
            role = msg.get("role")
            content = self._extract_response_text(msg.get("content", ""))
            if role == "user":
                if current_user is not None:
                    turns.append({"user": current_user, "assistant": None})
                current_user = content
            elif role == "assistant":
                turns.append({"user": current_user, "assistant": content})
                current_user = None

        if current_user is not None:
            turns.append({"user": current_user, "assistant": None})
        return {"turns": turns}

    async def get_improvement_insights(self, transcript_text: str):
        existing_rules = self.load_rules()
        response = await generate_insights_from_transcript(transcript_text, existing_rules)
        
        final_active_rules = response.get("final_active_rules", [])
        
        updated_rule_strings = []
        for rule_obj in final_active_rules:
            if isinstance(rule_obj, dict) and "rule" in rule_obj:
                updated_rule_strings.append(rule_obj["rule"])
            elif isinstance(rule_obj, str):
                updated_rule_strings.append(rule_obj)
                
        if updated_rule_strings:
            self.save_rules(updated_rule_strings)
            
        return response

    async def answer_user(self, transcript_input: str, previous_messages: list = None, conversation_state: dict = None, system_prompt: str = ""):
        if previous_messages is None:
            previous_messages = []
        if conversation_state is None:
            conversation_state = {"summary_generated": False, "conversation_summary": "No prior context."}

        # Build prompt dependencies
        conversation_state["summary_generated"] = False
        conversation_summary = self.generate_summary(previous_messages, conversation_state)
        
        current_rules_list = self.load_rules()
        rules_string = "\n".join([f"- {rule}" for rule in current_rules_list])
        
        user_prompt = self.build_user_prompt(conversation_summary, transcript_input, rules_string)
        
        payload = {
            "variables": {"systemPrompt": system_prompt},
            "userInput": user_prompt,
            "asyncOutput": False,
        }
        headers = {
            "X-API-KEY": self.api_key or "",
            "Content-Type": "application/json",
        }

        # Non-blocking async API call
        async with aiohttp.ClientSession() as session:
            async with session.post(self.airia_answers_pipeline_url, headers=headers, json=payload, timeout=30) as resp:
                resp.raise_for_status()
                response_json = await resp.json()
                
        # Parse output properly
        assistant_output = ""
        if isinstance(response_json, str):
            assistant_output = response_json
        elif isinstance(response_json, dict):
            assistant_output = (
                response_json.get("output")
                or response_json.get("result")
                or response_json.get("message")
                or response_json.get("output_text")
                or json.dumps(response_json)
            )
        else:
            assistant_output = str(response_json)

        # Update tracking list
        previous_messages.append({"role": "user", "content": transcript_input})
        previous_messages.append({"role": "assistant", "content": assistant_output})
        conversation_state["summary_generated"] = False
        self.generate_summary(previous_messages, conversation_state)

        return {
            "assistant_output": assistant_output,
            "previous_messages": previous_messages,
            "conversation_state": conversation_state,
            "conversation_turns_json": self.messages_as_turn_json(previous_messages),
        }
