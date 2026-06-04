"""'키 : 값, 키 : 값, ...' 형태의 문자열을 딕셔너리로 파싱한다.

예) 나이 : 20, 성별 : F, 고혈압 : T, 음식 메뉴 : ["식전 빵", "파스타"]
"""

import ast


# 필드마다 T/F 의 의미가 다르므로(성별 F=여성, 고혈압 F=False) 타입을 명시한다.
# 정의되지 않은 필드는 문자열로 처리된다.
FIELD_TYPES = {
    "나이": "int",      # 정수
    "성별": "str",      # 문자열 (F=여성, M=남성)
    "고혈압": "bool",    # 불리언 (T=True, F=False)
    "음식 메뉴": "list",  # 리스트
}

# bool 타입에서 참으로 인정할 값들
TRUE_VALUES = {"T", "TRUE", "1", "Y", "YES", "참"}


def _split_top_level(text, sep=","):
    """대괄호/중괄호/소괄호 '밖'에 있는 구분자만 기준으로 문자열을 나눈다.

    리스트 값 ["식전 빵", "파스타"] 안의 콤마가 잘리지 않도록 괄호 깊이를 추적한다.
    """
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _convert(value, field_type):
    """문자열 value 를 지정된 타입으로 변환한다."""
    value = value.strip()
    if field_type == "int":
        return int(value)
    if field_type == "float":
        return float(value)
    if field_type == "bool":
        return value.upper() in TRUE_VALUES
    if field_type == "list":
        # '["식전 빵", "파스타"]' 같은 문자열을 실제 list 로 안전하게 변환
        return ast.literal_eval(value)
    return value  # 그 외에는 문자열 그대로


def parse_record(text, field_types=FIELD_TYPES):
    """문자열 한 줄을 파싱해 딕셔너리로 반환한다."""
    record = {}
    for pair in _split_top_level(text, ","):
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)       # 첫 번째 ':' 만 기준으로 분리
        key = key.strip()
        field_type = field_types.get(key, "str")  # 미정의 필드는 문자열 취급
        record[key] = _convert(value, field_type)
    return record


if __name__ == "__main__":
    raw = '나이 : 20, 성별 : F, 고혈압 : T, 음식 메뉴 : ["식전 빵", "파스타"]'
    result = parse_record(raw)
    print(result)
    # {'나이': 20, '성별': 'F', '고혈압': True, '음식 메뉴': ['식전 빵', '파스타']}
