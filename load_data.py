"""
load_data.py — Bulk-load the nutrition Excel files into the database.

Source files (place under data/, see data/README.md):
    음식DB.xlsx            → 영양성분DB  (per-food nutrient content)
    영양소권장섭취량.xlsx   → 영양소조건  (recommended intake by sex & age band)

Inserts are parameterized (%s) and upsert via ON CONFLICT, so re-running is
safe and food names with apostrophes don't break the query.

Run:
    python load_data.py
"""

import math

import pandas as pd

from db import get_db

FOOD_XLSX = "data/음식DB.xlsx"
CONSTRAINT_XLSX = "data/영양소권장섭취량.xlsx"

# The 권장섭취량 sheet has a few header/label rows before the actual data.
CONSTRAINT_SKIP_ROWS = 3


def _f(v):
    """float, or None for NaN/blank (→ SQL NULL)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(v)


def load_food_db(db, df):
    """음식DB.xlsx → 영양성분DB (식품명 기준 upsert). 당류는 스키마에 없어 제외."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    rows = [(
        str(r["식품명"]),
        _f(r["에너지(kcal)"]), _f(r["단백질(g)"]), _f(r["지방(g)"]),
        _f(r["탄수화물(g)"]), _f(r["나트륨(mg)"]),
    ) for _, r in df.iterrows()]

    return db.executemany(
        "INSERT INTO 영양성분DB (식품명, 에너지, 단백질, 지방, 탄수화물, 나트륨) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (식품명) DO UPDATE SET "
        "에너지=EXCLUDED.에너지, 단백질=EXCLUDED.단백질, 지방=EXCLUDED.지방, "
        "탄수화물=EXCLUDED.탄수화물, 나트륨=EXCLUDED.나트륨",
        rows)


def load_constraints(db, df):
    """영양소권장섭취량.xlsx → 영양소조건 ((성별, 연령대) 기준 upsert)."""
    df = df.copy()
    df.columns = df.columns.str.strip()        # '단백질(g) ' 등 끝 공백 제거
    df = df.iloc[CONSTRAINT_SKIP_ROWS:]        # 앞쪽 헤더/라벨 행 건너뛰기
    rows = [(
        str(r["성별"]),
        int(r["연령대 하한"]), int(r["연령대 상한"]),
        _f(r["에너지(kcal)"]), _f(r["단백질(g)"]), _f(r["지방(g)"]),
        _f(r["탄수화물(g)"]), _f(r["나트륨(mg)"]),
    ) for _, r in df.iterrows()]

    return db.executemany(
        "INSERT INTO 영양소조건 "
        "(성별, 연령대_하한, 연령대_상한, 에너지, 단백질, 지방, 탄수화물, 나트륨) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (성별, 연령대_하한, 연령대_상한) DO UPDATE SET "
        "에너지=EXCLUDED.에너지, 단백질=EXCLUDED.단백질, 지방=EXCLUDED.지방, "
        "탄수화물=EXCLUDED.탄수화물, 나트륨=EXCLUDED.나트륨",
        rows)


def main():
    db = get_db(reset=True)        # clean schema, then load
    food_df = pd.read_excel(FOOD_XLSX)
    constraint_df = pd.read_excel(CONSTRAINT_XLSX)
    print("영양성분DB:", load_food_db(db, food_df), "rows")
    print("영양소조건:", load_constraints(db, constraint_df), "rows")
    db.close()


if __name__ == "__main__":
    main()
