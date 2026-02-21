import json
import asyncio
import requests
from app.core.config import settings

# Dedicated system prompt for insight generation
INSIGHT_GENERATION_PROMPT = """
You are an expert conversational AI analyst. 
Your goal is to review transcripts of an AI scheduling assistant speaking with users and identify ways to improve the system's instructions.
You will be provided with:
1. The current list of assistant instructions/rules.
2. A new conversation transcript.

Focus on:
1. Did the assistant collect all necessary information efficiently?
2. Were there points of confusion or repeated questions?
3. Did the assistant sound overly robotic or unnatural?

IMPORTANT: 
- Do not over-fit or add a new rule for every single user's quirk. Only introduce new rules, or modify existing ones, if there is a systemic pattern of failure or a clearly missing instruction.
- If a current rule is causing problems, you should modify or remove it.
- If the conversation went perfectly and the current rules are sufficient, do not hallucinate improvements. Simply return the exact same list of rules you were given.
- If the current list of rules is completely empty (i.e. []), you should create the first set of rules from scratch based on the transcript's failures. If the list is empty AND the conversation went perfectly, just return an empty list.

Output a JSON object with exactly two keys:
1. "insights": A list of specific findings or observations findings from the transcript. (Empty list if no issues)
2. "final_active_rules": The COMPLETE, updated list of rules the system should use going forward. Each object in the list must contain a "rule" (string value) and a "confidence_score" (integer between 0 and 100 representing how confident you are in this rule being active).

Example Output (Issues found, rules updated):
{
    "insights": [
        "The bot should ask for user phone number earlier.",
        "Users seem confused when asked about alternative dates."
    ],
    "final_active_rules": [
        {
            "rule": "Always ask for the user's phone number as the second question.",
            "confidence_score": 90
        },
        {
            "rule": "When asking for dates, provide a format example like (e.g. MM/DD/YYYY).",
            "confidence_score": 85
        }
    ]
}

Example Output (No issues found, returned existing rules exactly):
{
    "insights": [],
    "final_active_rules": [
        {
            "rule": "Always ask for the user's phone number as the second question.",
            "confidence_score": 90
        }
    ]
}
"""

async def generate_insights_from_transcript(transcript_text: str, existing_rules: list[str] = None) -> dict:
    """
    Calls the Gemini 3 model with the given transcript, existing rules, and system prompt
    to generate the final updated list of rules.
    
    Args:
        transcript_text (str): The conversation transcript to analyze.
        existing_rules (list[str]): The current set of rules for the assistant.
        
    Returns:
        dict: A dictionary containing insights and the final_active_rules.
    """
    if existing_rules is None:
        existing_rules = []
        
    url = "https://api.airia.ai/v2/PipelineExecution/0ae3c33d-f823-4819-bd52-14fb23b5027b"
    
    # transcript_text = """
    #     current_rules:[]
    #     conversation: [{"user": "I want to book an appointment"
    #     },
    #     {"agent": "Sure, I can help you with that"},
    #     {"user": I want to book it on next thursday},
    #     {"agent": "Sorry, I didnt catch that"}
    #     {"user": "bye"}]
    # """
    # Bundle the transcript and the existing rules into a single string for the Airia pipeline
    user_input = f"EXISTING RULES:\n{json.dumps(existing_rules, indent=2)}\n\nTRANSCRIPT:\n{transcript_text}"

    payload = json.dumps({
        "userInput": user_input,
        "asyncOutput": False
    })
    
    headers = {
        "X-API-KEY": settings.AIRIA_API_KEY_ANALYZER or "",
        "Content-Type": "application/json"
    }

    print("Calling Airia API pipeline...")
    # Make the HTTP request in a thread pool to avoid blocking the async event loop
    try:
        response = await asyncio.to_thread(
            requests.post,
            url,
            headers=headers,
            data=payload
        )
        response.raise_for_status()
        
        # Depending on how the Airia pipeline returns data, we attempt to parse it.
        # Often it returns a JSON object containing an "output" field with the LLM string.
        response_json = response.json()
        output_text = response_json.get("result", "")
        print("Output: ", output_text)
        
        if not output_text:
            # Fallback if the strict "output" field doesn't exist but the top level has what we need
            output_text = response.text
        
        # Clean markdown wrappers if the model returned them
        if output_text.startswith("```json"):
            output_text = output_text[7:]
        elif output_text.startswith("```"):
            output_text = output_text[3:]
        if output_text.endswith("```"):
            output_text = output_text[:-3]
            
        output_text = output_text.strip()
        
        final_data = json.loads(output_text)
        
        # Ensure the schema strictly matches our expectation even if the LLM hallucinated keys
        return {
            "insights": final_data.get("insights", []),
            "final_active_rules": final_data.get("final_active_rules", [])
        }
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM JSON output from Airia: {e}")
        print("Raw output string was:", output_text)
        return {"insights": [], "final_active_rules": existing_rules}
    except Exception as e:
        print(f"Error calling Airia API: {e}")
        return {"insights": [], "final_active_rules": existing_rules}
