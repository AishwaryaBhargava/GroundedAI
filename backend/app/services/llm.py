import json
import logging
from typing import Any, Dict

from openai import AzureOpenAI

from app.core.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_CHAT_DEPLOYMENT,
    AZURE_OPENAI_CHAT_API_VERSION,
)

logger = logging.getLogger(__name__)

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_CHAT_API_VERSION,
)

SYSTEM_PROMPT = """
You are a document-grounded QA system.

RULES (ABSOLUTE):
- Use ONLY the provided sources.
- Every factual statement MUST be supported by a citation.
- Citations MUST reference document_id and chunk_index from the sources.
- If the answer is not fully supported, respond with:
  { "refused": true, "refusal_reason": "Not found in provided documents" }
- Do NOT use prior knowledge.
- Do NOT guess.
- Output MUST be valid JSON.
"""

REFUSAL_FALLBACK = {
    "refused": True,
    "refusal_reason": "Not found in provided documents",
}

def _safe_json_parse(raw: str) -> Dict[str, Any]:
    """
    Parse JSON safely. Any failure becomes a refusal.
    """
    try:
        return json.loads(raw)
    except Exception as e:
        logger.warning("LLM returned invalid JSON: %s", e)
        return REFUSAL_FALLBACK


def _validate_llm_output(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure LLM output matches expected contract.
    """
    # Explicit refusal path
    if obj.get("refused") is True:
        return {
            "refused": True,
            "refusal_reason": obj.get(
                "refusal_reason", "Not found in provided documents"
            ),
        }

    # Must have answer + citations
    answer = obj.get("answer")
    citations = obj.get("citations")

    if not isinstance(answer, str) or not isinstance(citations, list):
        logger.warning("Malformed LLM output structure")
        return REFUSAL_FALLBACK

    # Validate citation keys (do NOT trust model)
    normalized_citations = []
    for c in citations:
        if (
            not isinstance(c, dict)
            or "document_id" not in c
            or "chunk_index" not in c
        ):
            logger.warning("Invalid citation detected from LLM")
            return REFUSAL_FALLBACK

        normalized_citations.append(
            {
                "document_id": c["document_id"],
                "chunk_index": c["chunk_index"],
            }
        )

    return {
        "answer": answer,
        "citations": normalized_citations,
        "refused": False,
    }


# def generate_grounded_answer(query: str, context: str) -> Dict[str, Any]:
#     """
#     Generate a grounded answer.
#     This function NEVER raises.
#     """
#     try:
#         response = client.chat.completions.create(
#             model=AZURE_OPENAI_CHAT_DEPLOYMENT,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {
#                     "role": "user",
#                     "content": f"""
# QUESTION:
# {query}

# SOURCES:
# {context}

# Return ONLY valid JSON in this format:
# {{
#   "answer": string,
#   "citations": [
#     {{ "document_id": string, "chunk_index": number }}
#   ]
# }}
# OR
# {{
#   "refused": true,
#   "refusal_reason": string
# }}
# """,
#                 },
#             ],
#         )

#         raw = response.choices[0].message.content
#         parsed = _safe_json_parse(raw)
#         return _validate_llm_output(parsed)

#     except Exception as e:
#         logger.exception("LLM call failed")
#         return REFUSAL_FALLBACK
    
def generate_grounded_answer(query: str, context: str) -> Dict[str, Any]:
    """
    Generate a grounded answer.
    This function NEVER raises.
    Returns validated content + metadata.
    """
    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""
QUESTION:
{query}

SOURCES:
{context}

Return ONLY valid JSON in this format:
{{
  "answer": string,
  "citations": [
    {{ "document_id": string, "chunk_index": number }}
  ]
}}
OR
{{
  "refused": true,
  "refusal_reason": string
}}
""",
                },
            ],
        )

        raw = response.choices[0].message.content
        parsed = _safe_json_parse(raw)
        validated = _validate_llm_output(parsed)

        # 🔹 Attach metadata AFTER validation
        return {
            **validated,
            "model": AZURE_OPENAI_CHAT_DEPLOYMENT,
            "token_usage": response.usage.total_tokens if response.usage else None,
        }

    except Exception:
        logger.exception("LLM call failed")
        return {
            **REFUSAL_FALLBACK,
            "model": AZURE_OPENAI_CHAT_DEPLOYMENT,
            "token_usage": None,
        }


SUMMARY_SYSTEM_PROMPT = """
You are a document summarization system.

You MUST output valid JSON with EXACTLY this schema:

{
  "bullet_points": string[],          // 5–10 concise bullets
  "narrative_summary": string,        // 1–3 paragraphs
  "suggested_questions": string[]     // 5–8 user questions
}

RULES (ABSOLUTE):
- Use ONLY the provided document content.
- Do NOT invent facts.
- Do NOT omit any field.
- Do NOT rename fields.
- Do NOT return markdown.
- Output JSON ONLY. No commentary.
"""

def get_summary_completion(context: str) -> dict:
    response = client.chat.completions.create(
        model=AZURE_OPENAI_CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
DOCUMENT CONTENT:
{context}

Return ONLY valid JSON.
"""
            },
        ],
    )

    parsed = json.loads(response.choices[0].message.content)

    return {
        "summary": parsed,
        "meta": {
            "model": response.model,
            "token_usage": response.usage.total_tokens if response.usage else None,
        },
    }
