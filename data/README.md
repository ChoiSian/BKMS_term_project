# data/

Place the two source spreadsheets here before running `load_data.py`.
They are **not** committed to the repo (see `.gitignore`).

| File | Loaded into | Expected columns |
|---|---|---|
| `음식DB.xlsx` | `영양성분DB` | `식품명`, `에너지(kcal)`, `단백질(g)`, `지방(g)`, `탄수화물(g)`, `당류(g)`, `나트륨(mg)` |
| `영양소권장섭취량.xlsx` | `영양소조건` | `성별`, `연령대 하한`, `연령대 상한`, `에너지(kcal)`, `단백질(g)`, `지방(g)`, `탄수화물(g)`, `나트륨(mg)` |

Notes:
- `당류(g)` is read but not stored (`영양성분DB` has no 당류 column).
- The 권장섭취량 sheet has a few header/label rows at the top; `load_data.py`
  skips them (`CONSTRAINT_SKIP_ROWS = 3`). Adjust if your file differs.
- `food_matrix.csv` (food-name embeddings) is generated here on the first run
  of `main.py` and cached for subsequent runs.
