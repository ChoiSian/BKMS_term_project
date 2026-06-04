"""
parse_input.py — Turn a free-form Korean self-description into a typed record.
"""

import ast

from llm import call_llm


def parse_input(prompt: str) -> str:
    request = (
        "다음을 읽고 나이, 성별, 음식 메뉴를 parse해주세요.\n"
        "나이는 정수형, 성별은 M/F의 문자열, 음식 메뉴는 문자열의 리스트로 반환해주세요.\n"
        "응답은 나이 : int, 성별 : str, 음식 메뉴 : [str] 꼴로만 만들고 "
        "다른 설명은 붙이지 말아주세요.\n"
    )
    return call_llm(request + prompt)


FIELD_TYPES = {"나이": "int", "성별": "str", "음식 메뉴": "list"}
TRUE_VALUES = {"T", "TRUE", "1", "Y", "YES", "참"}


def _split_top_level(text, sep=","):
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _convert(value, field_type):
    value = value.strip()
    if field_type == "int":
        return int(value)
    if field_type == "bool":
        return value.upper() in TRUE_VALUES
    if field_type == "list":
        return ast.literal_eval(value)
    return value


def parse_record(text, field_types=FIELD_TYPES):
    record = {}
    for pair in _split_top_level(text, ","):
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        key = key.strip()
        record[key] = _convert(value, field_types.get(key, "str"))
    return record
