"""Gemini client for the Game Master.

Uses Gemini's structured output (JSON schema) so the app can read the
inventory, solved puzzles and escape flag from every reply.
Key and model come from .env (see config.py).
Set MOCK_LLM=1 to run the UI without an API key (canned replies).
"""
import json
import os

from pydantic import BaseModel, Field

TEMPERATURE = 0.7

ERROR_HINTS = {
    400: "Bad request - check GEMINI_MODEL in .env.",
    401: "Invalid API key - check GEMINI_API_KEY in .env.",
    403: "Access denied - check the key, project access and that the free tier is enabled in AI Studio.",
    404: "Model not found - check GEMINI_MODEL in .env against the models your project can use.",
    429: "Free-tier rate limit or quota reached. Wait a moment and try again.",
}


class GMResponse(BaseModel):
    narration: str = Field(description="Text shown to the player")
    inventory: list[str] = Field(description="All items the player currently holds")
    solved: list[str] = Field(description="Puzzle ids solved so far")
    escaped: bool = Field(description="True only when the door was just opened")


class LLMError(Exception):
    """Friendly error shown in the UI."""


class GameMaster:
    def __init__(self, api_key: str, model: str, system_prompt: str):
        self.system_prompt = system_prompt
        self.model = model
        self.mock = os.getenv("MOCK_LLM") == "1"
        if not self.mock:
            from google import genai
            self.client = genai.Client(api_key=api_key)

    def respond(self, history: list[dict]) -> GMResponse:
        """history: list of {"role": "user"|"model", "text": str}, last item is the player's turn."""
        if self.mock:
            return _mock_reply(history)

        from google.genai import errors, types

        contents = [
            types.Content(role=m["role"], parts=[types.Part(text=m["text"])])
            for m in history
        ]
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=TEMPERATURE,
            response_mime_type="application/json",
            response_schema=GMResponse,
        )
        try:
            resp = self.client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except errors.APIError as e:
            hint = ERROR_HINTS.get(e.code, "")
            raise LLMError(f"Gemini API error ({e.code}): {e.message}. {hint}".strip()) from e
        except Exception as e:  # network/connection problems
            raise LLMError(f"Could not reach Gemini: {type(e).__name__}. Check your connection and try again.") from e

        if isinstance(resp.parsed, GMResponse):
            return resp.parsed
        try:
            return GMResponse(**json.loads(resp.text))
        except Exception as e:
            raise LLMError("The Game Master mumbled something unreadable. Please try again.") from e


def _mock_reply(history: list[dict]) -> GMResponse:
    """Tiny offline stand-in so the UI can be tested without an API key."""
    last = history[-1]["text"].lower()
    prev = [json.loads(m["text"]) for m in history if m["role"] == "model"]
    inv = prev[-1]["inventory"] if prev else []
    solved = prev[-1]["solved"] if prev else []
    if "0418" in last:
        return GMResponse(narration="The keypad flashes green. You are free!", inventory=inv, solved=solved, escaped=True)
    if "desk" in last and "note" not in inv:
        inv = inv + ["note"]
    return GMResponse(narration=f"(mock) You try: {history[-1]['text']}", inventory=inv, solved=solved, escaped=False)
