import os

from db import get_db
from parse_input import parse_input, parse_record
from food_matcher import FoodMatcher
from advisor import map_sql_query

MATRIX_PATH = "data/food_matrix.csv"   # cached food embeddings (built on first run)


def build_matcher(db):
    foods = [r["식품명"] for r in
             db.query("SELECT 식품명 FROM 영양성분db ORDER BY 식품명")]
    matcher = FoodMatcher(foods, matrix_path=MATRIX_PATH)
    if not os.path.exists(MATRIX_PATH):
        matcher.save_matrix(MATRIX_PATH)
    return matcher


def main():
    db = get_db()                      
    matcher = build_matcher(db)
    text = input("성별과 나이, 오늘 하루 식단을 알려주세요 : ")
    record = parse_record(parse_input(text))
    advice = map_sql_query(db, matcher, record)
    print(advice)
    db.close()
    

if __name__ == "__main__":
    main()
