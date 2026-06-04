"""
advisor.py — NL2SQL pipeline: meal plan → nutrient totals → personalized advice.

map_sql_query(db, matcher, input_dict):
    1. LLM writes SQL to fetch this user's recommended intake from 영양소조건.
    2. Each food (canonicalized via FoodMatcher) → LLM writes SQL to read its
       nutrients from 영양성분DB; the day's totals are summed.
    3. LLM writes advice comparing recommended vs. planned intake.

LLM-generated SQL is passed through _clean_sql() to strip stray markdown fences.
"""

from llm import call_llm
from food_matcher import make_food_list

NUTRIENTS = ["에너지", "단백질", "지방", "탄수화물", "나트륨"]


def _clean_sql(text: str) -> str:
    """Strip ```sql ... ``` fences the LLM sometimes adds despite instructions."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t.strip("`")
        t = t.rsplit("```", 1)[0]
    return t.strip()


def map_sql_query(db, matcher, input_dict):
    age = input_dict["나이"]
    sex = "남성" if input_dict["성별"] == "M" else "여성"
    food_list = make_food_list(matcher, input_dict["음식 메뉴"])

    # 1) recommended intake for this user (sex + age band)
    request = (
        "성별, 연령대_하한, 연령대_상한, 에너지, 단백질, 지방, 탄수화물, 나트륨을 열로 가지는 "
        "영양소조건이라는 이름의 DB에서 다음을 찾는 SQL 쿼리를 만들어주세요.\n"
        "Return ONLY the SQL statement. No markdown, no explanation.\n"
        f"성별은 {sex}이고, 나이는 {age}일 때 "
        "에너지, 단백질, 지방, 탄수화물, 나트륨의 값을 구해주세요."
    )
    constraint = db.query_one(_clean_sql(call_llm(request)))

    # 2) planned intake = sum of each food's nutrients
    totals = {n: 0.0 for n in NUTRIENTS}
    for food in food_list:
        request = (
            "다음 음식에 대해서 영양성분DB에서 에너지, 단백질, 지방, 탄수화물, 나트륨을 "
            "찾는 SQL 쿼리를 만들어주세요."
            "Return ONLY the SQL statement. No markdown, no explanation.\n"
            f"음식 이름은 {food}입니다. 음식 이름은 식품명이라는 열에 있습니다."
        )
        row = db.query_one(_clean_sql(call_llm(request)))
        if row:
            for n in NUTRIENTS:
                totals[n] += row[n] or 0.0

    # 3) personalized advice
    request = (
        "하루에 섭취해야 하는 영양소와 실제 섭취할 영양소가 항목 별로 다음과 같을 때 "
        "사용자를 위한 적절한 조언을 구체적인 수치를 언급하면서 해주세요.\n"
        "에너지, 단백질, 지방, 탄수화물, 나트륨 모두에 대해서 평가해주고 "
        "**와 같이 마크다운 문법은 절대 쓰지 마세요. 완결된 구조로 주세요.\n"
    )
    for n in NUTRIENTS:
        request += (f"{n}의 권장 섭취량은 {constraint[n]}이고 "
                    f"실제 섭취 예정량은 {totals[n]}입니다.\n")
    return call_llm(request)
