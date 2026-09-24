from pydantic import BaseModel

from app.services.generation import generate_structured

# Same reasoning as MAX_FLASHCARDS_PER_DOCUMENT in flashcard_generation.py -
# a bounded but generous target so one Gemini call can cover a typical
# lecture-notes document without trying to cram a 40-page PDF into 3
# questions or pad out a short handout to 20.
MAX_QUESTIONS_PER_TEST = 10


class TestQuestionContent(BaseModel):
    """The shape we constrain Gemini's output to for a single practice
    test question - a short-answer question plus the answer it's graded
    against. Kept to just these two fields for the same reason
    FlashcardContent is: it's what makes generate_structured's schema
    validation meaningful, and it's all TestQuestion actually stores.
    """

    question: str
    correct_answer: str


class PracticeTestBatch(BaseModel):
    """The response_schema passed to Gemini - the whole test's worth of
    questions in one call, not one call per question. Same reasoning as
    FlashcardBatch: a single prompt asking for a coherent set produces
    better-spread, less repetitive questions than N independent calls,
    and it's one API call against the team's Gemini quota per test.
    """

    questions: list[TestQuestionContent]


_PROMPT_INSTRUCTIONS = (
    "You are creating a short-answer practice test from the material "
    f"below. Generate up to {MAX_QUESTIONS_PER_TEST} questions that test "
    "a student's understanding of the most important concepts, "
    "definitions, and facts in this material.\n\n"
    "Guidelines:\n"
    "- Each question should be answerable in a short phrase or "
    "sentence, not an essay - this is a short-answer test, not a "
    "long-form one.\n"
    "- Each correct_answer should be the specific, unambiguous answer "
    "the question is looking for.\n"
    "- Do not create near-duplicate questions that test the same fact "
    "twice.\n"
    "- Cover a spread of the material rather than clustering every "
    "question around one section."
)


def generate_practice_test_questions(extracted_text: str) -> list[TestQuestionContent]:
    """Generate a set of short-answer practice test questions from a
    document's extracted text.

    One Gemini call for the whole test, not one call per question -
    same reasoning as generate_flashcards.
    """
    prompt = (
        f"{_PROMPT_INSTRUCTIONS}\n\n"
        "Study material:\n\n"
        f"{extracted_text}"
    )

    result = generate_structured(prompt, response_schema=PracticeTestBatch)
    return result.questions
