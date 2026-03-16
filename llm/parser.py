import json
import re
from typing import Optional

from pydantic import BaseModel, field_validator
from core.logger import get_logger

log = get_logger("llm.parser")

ALLOWED_ACTIONS = {
    "wait", "move", "click", "double_click", "right_click", "scroll",
    "type", "key", "hotkey", "key_down", "key_up",
    "open_app", "run_command", "focus_window", "close_window", "maximize_window",
    "upload_file", "create_file", "read_file",
}


class ActionStep(BaseModel):
    type: str
    # All other fields are dynamic and passed as-is
    model_config = {"extra": "allow"}

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"Action type '{v}' is not allowed")
        return v


def parse_actions(llm_response: str) -> list[dict]:
    json_str = _extract_json(llm_response)
    if not json_str:
        log.error("No JSON block found in LLM response")
        return []

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON from LLM response: {e}")
        return []

    if isinstance(raw, dict):
        raw = raw.get("actions", [raw])
    if not isinstance(raw, list):
        log.error("LLM response is not a list of actions")
        return []

    valid_actions = []
    for i, item in enumerate(raw):
        try:
            action = ActionStep(**item)
            valid_actions.append(action.model_dump())
        except Exception as e:
            log.warning(f"Skipping invalid action at index {i}: {e}")

    log.info(f"Parsed {len(valid_actions)} valid actions from LLM response")
    return valid_actions


def parse_single_action(llm_response: str) -> Optional[dict]:
    """Parse a single action or done signal from LLM response (used in vision loop)."""
    json_str = _extract_json(llm_response)
    if not json_str:
        json_str = llm_response.strip()

    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse single action JSON: {e} | response: {llm_response[:200]}")
        return None

    if not isinstance(raw, dict):
        log.error("Single action response is not a JSON object")
        return None

    if raw.get("done") is True:
        return {"done": True, "message": raw.get("message", "Task complete")}

    try:
        action = ActionStep(**raw)
        return action.model_dump()
    except Exception as e:
        log.warning(f"Invalid single action: {e} | raw: {raw}")
        return None


def _extract_json(text: str) -> Optional[str]:
    pattern = r"```(?:json)?\s*\n?([\s\S]*?)```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()

    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

    return None
