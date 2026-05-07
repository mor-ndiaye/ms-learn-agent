import json
from pathlib import Path
from typing import Dict

from ms_learn_client import MsLearnClient

# Load user profile Path file
USER_PROFILE = Path("user_profile.json")

# Initialize the MsLearnClient
ms_client = MsLearnClient()

#  Tools definition (3 tools: search_ms_learn_courses, get_user_profile, get_course_details)

TOOLS = [
    {
        "name": "search_ms_learn_courses",
        "description": (
            "Search Microsoft Learn courses by query. Returns up to `max_results` courses (default 5). "
            "Optional `level` filter restricts to a target audience level."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query provided by the user for finding relevant courses",
                },
                "level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "The recommended level of the course. Either  beginner, intermediate or advanced",
                },
                "max_results": {
                    "type": "integer",
                    "description": "The maximum results to show to the user. e.g: 3 — default: 5",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve the user's profile information loaded from the user_profile.json file "
        "Use this tool to get information about the user's information like its name, level, current role, prefered courses languages and length, learning interests topics (primaries and secondaries), past completed and in progress courses, topics/subjects to avoid. "
        "This information can help tailor course recommendations for user's needs.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_course_details",
        "description": "Get a full course's details based on its unique uid. "
        "Use this tool to retrieve full details of a given course. "
        "The course details includes, among each others : uid, title, summary, targeted levels and roles, length duration, course's url and many others",
        "input_schema": {
            "type": "object",
            "properties": {
                "uid": {
                    "type": "string",
                    "description": "The unique identifier of a given course",
                },
            },
            "required": ["uid"],
        },
    },
]


def execute_tool(tool_name: str, tool_input: Dict) -> str:
    if tool_name == "search_ms_learn_courses":
        user_query: str = tool_input.get("query", "")

        kwargs = {"query": user_query}
        if level := tool_input.get("level"):
            kwargs["level"] = level
        if max_results := tool_input.get("max_results"):
            kwargs["max_results"] = max_results
        return json.dumps(ms_client.search_modules(**kwargs))
    elif tool_name == "get_user_profile":
        if USER_PROFILE.exists():
            return USER_PROFILE.read_text()
        return json.dumps({"error": "Unable to laod user profile", "status_code": 400})
    elif tool_name == "get_course_details":
        course_uid = tool_input.get("uid")
        course = ms_client.get_module_details(uid=course_uid)

        return (
            json.dumps(course)
            if course
            else json.dumps({"error": "Course not found.", "status_code": 404})
        )
    else:
        return json.dumps({"error": "Tool not found"})
