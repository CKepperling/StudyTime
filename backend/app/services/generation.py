import os
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# Flash, not Pro - per the team's earlier decision, Pro models sit
# behind Google's paid tier now, while Flash stays free and is more
# than capable for summarization/flashcard/test-question generation.
#
# Model names on Gemini move fast - gemini-2.5-flash was current when
# this file was first written, and was already retired for new API
# keys within weeks. If this model 404s again later with a message
# telling you to use a different name, that's the fix: swap the
# string below to whatever Google's own error message recommends.
DEFAULT_MODEL = "gemini-3.6-flash"

# One client, reused across every call - genai.Client() handles its
# own connection pooling internally, so there's no benefit to
# recreating it per request, and every module that imports this one
# shares the same client instance.
_client = genai.Client(api_key=GEMINI_API_KEY)

# Bound to BaseModel so type checkers know generate_structured()
# returns whatever specific Pydantic schema was passed in as
# response_schema, not just "some BaseModel".
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class GenerationError(Exception):
    """Raised when a Gemini call fails outright, OR succeeds but the
    response doesn't actually match the schema that was asked for.

    Every AI content generator (summaries, flashcards, practice tests,
    and anything added later) can catch this ONE exception type rather
    than needing to know about google.genai's own exception types or
    pydantic's ValidationError separately.
    """


def generate_structured(
    prompt: str,
    response_schema: type[SchemaT],
    model: str = DEFAULT_MODEL,
) -> SchemaT:
    """Send a prompt to Gemini and get back a validated, typed object.

    This is the ONE shared entry point every AI content generator is
    meant to call through. Each generator (T12's summaries, T13.5's
    flashcards, T16.5's practice tests, or whatever gets added after)
    supplies two things unique to itself:

      1. `prompt` - the actual instructions/content specific to that
         generator (e.g. "summarize this text at a Y difficulty level").
      2. `response_schema` - a Pydantic model describing the exact
         shape the response should take (e.g. a SummaryContent model
         with just a `text: str` field, or a FlashcardBatch model with
         a `cards: list[FlashcardContent]` field).

    Everything else - calling the API, asking Gemini to constrain its
    output to that schema, and validating what comes back - happens
    here ONCE, instead of being reimplemented per content type.

    response_schema passed to Gemini's config doesn't just describe
    the shape for OUR validation - it actively constrains what Gemini
    generates in the first place, which is what makes this meaningfully
    more reliable than just asking for "valid JSON" in the prompt text
    and hoping.
    """
    try:
        response = _client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
    except Exception as e:
        # google.genai can raise several different exception types
        # depending on what went wrong (network, auth, rate limit,
        # content safety block, etc.) - collapsing them all into one
        # GenerationError is deliberate, same reasoning as
        # decode_access_token in services/auth.py: callers just need
        # to know "did this work or not," not which of several
        # possible SDK exceptions it was.
        raise GenerationError(f"Gemini API call failed: {e}") from e

    try:
        return response_schema.model_validate_json(response.text)
    except Exception as e:
        # Schema-constrained output makes this rare, but not
        # impossible - a truncated response (hit a token limit
        # mid-generation) or a content-safety filter substituting an
        # empty response could both land here.
        raise GenerationError(
            f"Gemini response didn't match the expected schema: {e}"
        ) from e