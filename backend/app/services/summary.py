from pydantic import BaseModel

from app.models.summary import DifficultyLevel
from app.services.generation import generate_structured


class SummaryContent(BaseModel):
    """The shape we constrain Gemini's output to for a single summary -
    deliberately just one field. Keeping this minimal is what makes
    generate_structured's schema validation actually meaningful.
    """

    text: str


# One clear instruction per level, kept separate from the actual prompt
# builder below - if a future ticket wants to tune wording for one
# level without touching the others, this is the one place to do it.
_LEVEL_INSTRUCTIONS = {
    DifficultyLevel.EASY: (
        "Write this summary in plain, simple language that someone with "
        "no background in the subject could follow. Avoid jargon - if a "
        "technical term is unavoidable, briefly explain it in plain words."
        "Make this summary shorter and to the point."
    ),
    DifficultyLevel.MEDIUM: (
        "Write this summary at a level appropriate for an undergraduate "
        "student studying this subject - clear and well-organized, "
        "assuming some baseline familiarity with the topic."
        "Keep this summary to a standard readable length."
    ),
    DifficultyLevel.HARD: (
        "Write this summary at an advanced level, using precise technical "
        "terminology appropriate for a graduate student or someone "
        "already expert in this material."
        "This summary can be longer if needed as to explain more about the topic."
    ),
}


def generate_summary(extracted_text: str, level: DifficultyLevel) -> str:
    """Generate one summary of extracted_text at a given difficulty level.

    Deliberately one Gemini call per level, not one call asking for all
    three at once - a focused prompt with a single instruction produces
    more consistent results than asking for three different versions in
    one response, and it's what makes AUTO_GENERATE_SUMMARIES /
    generate-summaries's "regenerate everything" behavior in tasks.py
    straightforward: three independent calls, not one call to unpack.
    """
    instructions = _LEVEL_INSTRUCTIONS[level]
    prompt = (
        f"{instructions}\n\n"
        "Summarize the following study material:\n\n"
        f"{extracted_text}"
    )

    result = generate_structured(prompt, response_schema=SummaryContent)
    return result.text