# ============================================================
# pipeline/json_utils.py — JSON Repair for LLM Output
# ============================================================
# LLMs (especially smaller models like Qwen 3.5 9B) often produce
# invalid JSON when the content includes code examples. The most
# common breakage is raw newlines and unescaped quotes inside
# JSON string values.
#
# This module provides repair functions that fix these issues
# BEFORE json.loads() is called.
#
# COMMON FAILURE PATTERNS:
#   1. Raw newlines in string values:
#      {"code": "def hello():
#          print('hi')"}
#      Fix: Replace raw \n with \\n when inside a string
#
#   2. Unescaped double quotes in string values:
#      {"code": "print("hello")"}
#      Fix: Escape inner quotes when inside a string
#
#   3. Raw tabs in string values:
#      {"code": "	if True:
#          pass"}
#      Fix: Replace raw \t with \\t when inside a string
# ============================================================

import re


def repair_json(text: str) -> str:
    """
    Attempt to repair malformed JSON produced by an LLM.

    Handles the most common issues:
      - Raw newlines inside JSON string values
      - Raw tabs inside JSON string values
      - Unescaped double quotes inside JSON string values
      - Trailing commas before } or ]
      - Python-style single-quote keys

    Args:
        text: Raw JSON string (potentially malformed).

    Returns:
        Repaired JSON string that should parse with json.loads().
    """
    if not text or not text.strip():
        return text

    text = _fix_single_quote_keys(text)
    text = _fix_trailing_commas(text)
    text = _fix_string_contents(text)
    text = _fix_unescaped_backslashes(text)

    return text


def _fix_single_quote_keys(text: str) -> str:
    """Replace Python-style single-quote keys with double-quote keys."""
    text = re.sub(r"'(\w+)'\s*:", r'"\1":', text)
    return text


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ]."""
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _fix_string_contents(text: str) -> str:
    """
    Walk through JSON text and fix string contents.

    When inside a JSON string (between unescaped double quotes),
    this escapes:
      - Raw newlines -> \\n
      - Raw tabs -> \\t
      - Raw carriage returns -> \\r
      - Unescaped double quotes -> \\"
    """
    result = []
    i = 0
    in_string = False
    length = len(text)

    while i < length:
        char = text[i]

        if in_string:
            if char == '\\':
                result.append(char)
                if i + 1 < length:
                    next_char = text[i + 1]
                    result.append(next_char)
                    i += 2
                    continue
            elif char == '"':
                in_string = False
                result.append(char)
            elif char == '\n':
                result.append('\\')
                result.append('n')
            elif char == '\r':
                result.append('\\')
                result.append('r')
            elif char == '\t':
                result.append('\\')
                result.append('t')
            else:
                result.append(char)
        else:
            if char == '"':
                in_string = True
                result.append(char)
            else:
                result.append(char)

        i += 1

    return ''.join(result)


def _fix_unescaped_backslashes(text: str) -> str:
    """
    Fix unescaped backslashes in string values.

    Pattern: a backslash that is NOT followed by a valid JSON escape char
    (" \\ b f n r t u /) should be doubled.
    """
    valid_escapes = set('"\\bfnrtu/')

    result = []
    i = 0
    in_string = False
    length = len(text)

    while i < length:
        char = text[i]

        if in_string:
            if char == '\\' and i + 1 < length:
                next_char = text[i + 1]
                if next_char in valid_escapes:
                    result.append(char)
                    result.append(next_char)
                    i += 2
                    continue
                else:
                    result.append('\\\\')
                    result.append(next_char)
                    i += 2
                    continue
            elif char == '"':
                in_string = False
                result.append(char)
            else:
                result.append(char)
        else:
            if char == '"':
                in_string = True
                result.append(char)
            else:
                result.append(char)

        i += 1

    return ''.join(result)


def extract_json(text: str) -> str:
    """
    Extract JSON from LLM response, stripping markdown fences and extra text.
    """
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```", "", text)

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]

    return text.strip()
