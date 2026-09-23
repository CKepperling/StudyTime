from pydantic import BaseModel

from app.services.generation import generate_structured

# A generous but bounded target - Gemini won't always hit this exactly
# (the prompt asks for "up to" this many), but it keeps a single call
# from trying to cover a 40-page PDF with 3 cards or a short handout
# with 60.
MAX_FLASHCARDS_PER_DOCUMENT = 15


class FlashcardContent(BaseModel):
    """The shape we constrain Gemini's output to for a single flashcard -
    just the two fields a card actually needs. Same reasoning as
    SummaryContent in services/summary.py: keeping this minimal is what
    makes generate_structured's schema validation meaningful.
    """

    front: str
    back: str


class FlashcardBatch(BaseModel):
    """The actual response_schema passed to Gemini - a batch of cards
    in one call, not one call per card. One call asking for the whole
    set produces a more coherent, non-repetitive set of cards than N
    independent calls would, and it's far cheaper against the team's
    free-tier Gemini quota.
    """

    cards: list[FlashcardContent]


_PROMPT_INSTRUCTIONS = (
    "You are creating study flashcards from the material below. Generate "
    f"up to {MAX_FLASHCARDS_PER_DOCUMENT} flashcards that cover the most "
    "important concepts, definitions, and facts a student would need to "
    "know for an exam on this material.\n\n"
    "Guidelines:\n"
    "- Each flashcard's front should be a focused question or prompt, "
    "not a vague topic label.\n"
    "- Each flashcard's back should be a concise, correct answer - a "
    "sentence or two, not a full paragraph.\n"
    "- Do not create near-duplicate cards that test the same fact twice.\n"
    "- Cover a spread of the material rather than clustering every card "
    "around one section."
)


def generate_flashcards(extracted_text: str) -> list[FlashcardContent]:
    """Generate a set of flashcards from a document's extracted text.

    Deliberately one Gemini call for the whole batch, not one call per
    card - same reasoning as generate_summary makes one call per level
    instead of one call for everything, just inverted: here a SINGLE
    focused prompt asking for a coherent set produces better, less
    repetitive cards than N independent calls would, and it's what
    keeps a full document's worth of cards to one API call against the
    team's quota.
    """
    prompt = (
        f"{_PROMPT_INSTRUCTIONS}\n\n"
        "Study material:\n\n"
        f"{extracted_text}"
    )

    result = generate_structured(prompt, response_schema=FlashcardBatch)
    return result.cards
