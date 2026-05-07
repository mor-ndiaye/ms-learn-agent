import json
from anthropic import Anthropic
from dotenv import load_dotenv

from tools import TOOLS, execute_tool

# Setup (load env, init client Anthropic, init MsLearnClient, load profile path)
# Load vars in the .env* files
load_dotenv(dotenv_path="./.env.local")

# Initialize the Anthropic client
client = Anthropic()

SYSTEM_PROMPT = """
You are a personalized learning advisor specialized in tech and AI courses.

Your workflow:
1. ALWAYS start by retrieving the user's profile to understand their level,
   interests, and what they've already learned.
2. Search for relevant courses based on their query AND their profile context.
   Reformulate the search query if needed to better match their actual goals.
3. Filter out courses they've already completed or that match topics in their
   "avoid_topics" list.
4. If a course seems particularly relevant, use get_course_details to provide
   richer recommendations.
5. Present 2-4 top recommendations in a clear, structured format. For each
   recommendation, explain WHY it fits this specific user (based on their
   level, interests, or prior learning).

Be concise but personalized. The user is technical — skip basic explanations.
If no good matches exist, say so honestly and suggest alternative search angles.

IMPORTANT — When to STOP searching:
- If after 2 search attempts the results are not relevant to the user's
  actual goal, STOP searching and present what you found.
- Be honest: tell the user "Microsoft Learn's catalog doesn't seem to have
  strong matches for this specific topic" and suggest:
    a) The closest adjacent courses you did find
    b) Alternative topics they might explore
- Never exceed 3 search calls per user query. Quality over quantity.
"""


def _extract_text(response) -> str:
    return "\n".join(block.text for block in response.content if block.type == "text")


def agent_loop(user_message: str) -> str:
    print(f"user_message: {user_message}")

    messages = [{"role": "user", "content": user_message}]

    MAX_ITERATIONS: int = 5
    iter_counter: int = 1

    while iter_counter <= MAX_ITERATIONS:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        print(f"═══ Round {iter_counter}/{MAX_ITERATIONS} ═══")

        if response.stop_reason == "tool_use":
            tool_result_content = []
            for index, block in enumerate(response.content):
                if block.type == "tool_use":
                    print(f"🔧 Tool {index}: {block.name}({json.dumps(block.input)})")
                    tool_result = execute_tool(
                        tool_name=block.name, tool_input=block.input
                    )

                    tool_result_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result,
                        }
                    )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_result_content})
        elif response.stop_reason == "end_turn":
            return _extract_text(response)
        elif response.stop_reason == "max_tokens":
            raise RuntimeError("Response truncated, increase max_tokens")
        else:
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")

        iter_counter += 1
    print("⚠️ Max iterations reached, forcing a final response...")
    final_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT
        + "\n\nYou've used your tool budget. Give your best final recommendation based on what you've found so far.",
        messages=messages,
    )
    return final_response.content[0].text
