import json

import logging

import re


from openai import OpenAI

from google import genai


from app.config import settings

from app.llm.prompts import SYSTEM_PROMPT


logger = logging.getLogger(__name__)


# =====================================
# Groq Client
# =====================================

groq_client = OpenAI(

    base_url="https://api.groq.com/openai/v1",

    api_key=settings.GROQ_API_KEY

) if settings.GROQ_API_KEY else None



# =====================================
# Gemini Client
# =====================================

gemini_client = genai.Client(

    api_key=settings.GEMINI_API_KEY

) if settings.GEMINI_API_KEY else None



# =====================================
# JSON Cleaner
# =====================================

def clean_json(text):

    if text is None:
        raise ValueError("LLM response is empty.")

    text = str(text).strip()

    if not text:
        raise ValueError("LLM response is empty.")

    code_block_match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if code_block_match:
        text = code_block_match.group(1).strip()
    elif text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    bracket_start = text.find("[")
    bracket_end = text.rfind("]")

    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]
    elif bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
        text = text[bracket_start:bracket_end + 1]

    return text.strip()



def parse_json_response(raw_text):

    cleaned = clean_json(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("Primary JSON parse failed, retrying with fallback extraction: %s", exc)

        candidate = re.search(
            r"(\{.*\}|\[.*\])",
            cleaned,
            flags=re.DOTALL,
        )

        if candidate is None:
            raise ValueError(f"Could not extract JSON from LLM response: {cleaned[:400]}")

        payload = json.loads(candidate.group(1))

    if isinstance(payload, list):
        return {"directives": payload}

    if isinstance(payload, dict) and "directives" in payload:
        return payload

    if isinstance(payload, dict):
        return {"directives": [payload]}

    raise ValueError("LLM response did not contain a valid directives payload.")


# =====================================
# Groq Call
# =====================================

def call_groq(notes):

    if groq_client is None:
        raise ValueError("GROQ_API_KEY is not configured.")

    for attempt in range(2):
        try:
            response = groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(notes),
                    },
                ],
                temperature=0,
            )

            content = response.choices[0].message.content
            return parse_json_response(content)

        except Exception as exc:
            logger.warning("Groq attempt %s failed: %s", attempt + 1, exc)
            if attempt == 1:
                raise


# =====================================
# Gemini Call
# =====================================

def call_gemini(notes):

    if gemini_client is None:
        raise ValueError("GEMINI_API_KEY is not configured.")

    prompt = f"""

{SYSTEM_PROMPT}


Operator Notes:

{json.dumps(notes)}


Return ONLY JSON.

"""

    for attempt in range(2):
        try:
            response = gemini_client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )

            text = getattr(response, "text", "")
            return parse_json_response(text)

        except Exception as exc:
            logger.warning("Gemini attempt %s failed: %s", attempt + 1, exc)
            if attempt == 1:
                raise


# =====================================
# Main Interpreter
# =====================================

def interpret_notes(notes):

    logger.info("Attempting Groq interpretation...")

    try:
        return call_groq(notes)

    except Exception as exc:
        logger.exception("Groq failed: %s", exc)
        logger.info("Falling back to Gemini...")
        groq_error = str(exc)

    try:
        return call_gemini(notes)

    except Exception as exc:
        logger.exception("Gemini failed: %s", exc)
        raise Exception(
            f"All LLM providers failed. Groq: {groq_error}. Gemini: {exc}"
        ) from exc