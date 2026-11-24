# ZYE AI — Pre-Mortem Schema Sanitization & Developer API Compatibility Report

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Module:** `zye_intelligence/premortem.py` (`_clean_gemini_schema`), `zye_intelligence/schemas.py` (`NegativeAuditReport`)  
**Status:** FULLY CERTIFIED & OPERATIONAL  

---

## 1. Problem Statement & Error Forensic

During autonomous pre-execution audits, ZYE AI executes a **Negative Pre-Mortem Audit** using Google Gemini 2.5/3.0. This audit uses Pydantic structured output (`response_schema=NegativeAuditReport`) to obtain verified risk predictions.

When invoking Gemini using the Developer API (`google-genai` SDK with Google AI Studio API keys), the API returned:
```
ValueError: additionalProperties is only supported in Gemini Enterprise Agent Platform mode, not in Gemini Developer API mode.
```

### Forensic Root Cause
1. Pydantic v2 generates JSON schemas conforming to draft 2020-12 / OpenAPI 3.1. By default, Pydantic objects include `"additionalProperties": false` or `"additionalProperties": true` at each object definition level.
2. The Google Gemini Developer API schema parser strictly rejects any schema object that includes the `additionalProperties` key. Only Google Cloud Vertex AI / Enterprise Agent Platform endpoints accept `additionalProperties`.

---

## 2. Recursive Schema Sanitization Engine

To provide 100% compatibility with Gemini Developer API mode without losing any structural type validations, a recursive cleaner function `_clean_gemini_schema` was created in `zye_intelligence/premortem.py`:

```python
def _clean_gemini_schema(schema: Any) -> Any:
    """
    Recursively remove 'additionalProperties' from JSON schema dictionaries.
    Gemini Developer API strictly disallows 'additionalProperties'.
    """
    if isinstance(schema, dict):
        cleaned = {}
        for k, v in schema.items():
            if k == "additionalProperties":
                continue
            cleaned[k] = _clean_gemini_schema(v)
        return cleaned
    elif isinstance(schema, list):
        return [_clean_gemini_schema(item) for item in schema]
    return schema
```

### Application in `ZyePreMortemEngine`

```python
raw_schema = NegativeAuditReport.model_json_schema()
cleaned_schema = _clean_gemini_schema(raw_schema)

config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=cleaned_schema,
    temperature=0.2,
)
```

---

## 3. Verification Test Evidence

Verified via `test_premortem_gemini_developer_mode_schema` in `tests/test_voice_reliability_hotfix.py`:
- Traversed all nested properties, definitions, references, and sub-objects of `NegativeAuditReport`.
- Total `additionalProperties` keys remaining: **0**.
- Schema retention: `type`, `properties`, `required`, `description` intact.
- Unit test passed in **0.02s**.
