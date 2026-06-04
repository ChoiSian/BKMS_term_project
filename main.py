"""
main.py — Interactive personalized nutrition advisor (end-to-end).

Flow:
    natural-language input
      → parse_input + parse_record   (나이/성별/음식 메뉴)
      → FoodMatcher                  (음식명 → 식품명 정규화)
      → map_sql_query                (NL2SQL: 권장량/섭취량 조회 + 조언 생성)

Prereqs (one-time):
    1. python load_data.py     # populate 영양성분DB, 영양소조건 from Excel
    2. export OPENAI_API_KEY="sk-..."

Run:
    python main.py
"""

import os

from db import get_db
from parse_input import parse_input, parse_record
from food_matcher import FoodMatcher
from advisor import map_sql_query

MATRIX_PATH = "data/food_matrix.csv"   # cached food embeddings (built on first run)


def build_matcher(db):
    """Build (or load) the FoodMatcher over the 식품명 list in 영양성분DB."""
    foods = [r["식품명"] for r in
             db.query("SELECT 식품명 FROM 영양성분db ORDER BY 식품명")]
    matcher = FoodMatcher(foods, matrix_path=MATRIX_PATH)
    if not os.path.exists(MATRIX_PATH):
        matcher.save_matrix(MATRIX_PATH)
    return matcher


def main():
    db = get_db()                      # connect; schema already loaded by load_data.py
    matcher = build_matcher(db)

    text = input("성별과 나이, 오늘 하루 식단을 알려주세요 : ")
    record = parse_record(parse_input(text))
    advice = map_sql_query(db, matcher, record)
    print(advice)

    db.close()


if __name__ == "__main__":
    main()
