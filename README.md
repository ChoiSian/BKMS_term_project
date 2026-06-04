# BKMS Term Project: Personalized Nutrition Advisor (NL2SQL)

A conversational diet advisor. The user describes—in free-form Korean—their
age, sex, and the day's meal plan; the system parses it, matches each dish to a
canonical food in the nutrition database via embeddings, generates SQL
(NL2SQL) to look up recommended vs. planned intake, and produces personalized
dietary advice.

```
입력(자연어)  →  파싱  →  음식 임베딩 매칭  →  NL2SQL 조회  →  맞춤 조언
```

---

## File Structure

```
├── README.md            ← This file (setup & usage guide)
├── requirements.txt      ← Python dependencies
├── init_db.sql           ← Schema for 영양성분DB / 영양소조건 (reference)
├── db.py                 ← DB wrapper (connection, schema init, query/execute)
├── llm.py                ← OpenAI client + call_llm helper
├── parse_input.py        ← NL input → typed record (parse_input + parse_record)
├── load_data.py          ← Excel → 영양성분DB / 영양소조건 (parameterized upsert)
├── food_matcher.py       ← Embedding-based food-name matcher (multilingual-e5)
├── advisor.py            ← NL2SQL pipeline (map_sql_query) + advice generation
├── main.py               ← Interactive end-to-end entry point
└── data/
    ├── README.md         ← What spreadsheets to place here
    ├── 음식DB.xlsx              (not committed)
    └── 영양소권장섭취량.xlsx     (not committed)
```

---

## 1. Setup

### 1-1. Prerequisites

- Python 3.9+
- PostgreSQL 14+
- OpenAI API key
- (GPU optional, but recommended for the e5-large embeddings)

### 1-2. Install Python packages

```bash
pip install -r requirements.txt
```

### 1-3. Create and configure the database

```bash
createdb -U postgres textbook
```

Connection settings are read from environment variables (defaults in
parentheses):

```bash
export DB_HOST=localhost      # (localhost)
export DB_PORT=5432           # (5432)
export DB_NAME=textbook       # (textbook)
export DB_USER=postgres       # (postgres)
export DB_PASSWORD=dbclass    # (dbclass)
```

`init_db.sql` documents the schema, but `load_data.py` (and `db.py`) create it
automatically — no manual `psql` step is required.

### 1-4. Set your API key

```bash
export OPENAI_API_KEY="sk-..."
```

> ⚠️ Never hard-code the API key in source. Keys committed to git are
> compromised; rotate immediately if that happens.

---

## 2. Workflow

### Step 1: Load the data

Put `음식DB.xlsx` and `영양소권장섭취량.xlsx` under `data/` (see `data/README.md`),
then:

```bash
python load_data.py
```

This (re)creates the schema and upserts both tables. Re-running is safe
(`ON CONFLICT` upsert, no duplicates).

### Step 2: Run the advisor

```bash
python main.py
```

```
성별과 나이, 오늘 하루 식단을 알려주세요 : 나는 20살 여성이야. 아침엔 와플과
딸기 우유, 점심엔 식빵과 토마토 스파게티, 저녁엔 삼겹살 구이를 먹을 계획이야.
```

The first run builds the food-name embedding matrix and caches it to
`data/food_matrix.csv`; later runs load it instantly.

---

## 3. How it works (pipeline)

1. **`parse_input.py`** — `parse_input()` asks the LLM to extract
   `나이 / 성별 / 음식 메뉴`; `parse_record()` parses that line into a typed dict
   (bracket-aware split so the food list stays intact).
2. **`food_matcher.py`** — embeds the user's dish names and the DB's `식품명`
   list with `multilingual-e5-large`, then matches each dish to the nearest
   canonical food by cosine similarity (`query:` / `passage:` prefixes; the
   matrix is kept as a NumPy array so indexing stays aligned with `foods`).
3. **`advisor.py`** — `map_sql_query()`:
   - LLM → SQL for the user's recommended intake (`영양소조건`).
   - For each matched food, LLM → SQL for its nutrients (`영양성분DB`); sums the
     day's totals.
   - LLM → advice comparing recommended vs. planned intake.
   - LLM-generated SQL is passed through `_clean_sql()` to strip stray markdown
     fences.

---

## 4. Resetting the database

```bash
python -c "from db import get_db; get_db(reset=True).close()"   # drop + recreate schema
python load_data.py                                             # reload
```

---

## 5. Team & Contributions

| 팀원 | 역할 및 기여 내용 |
|---|---|
| 고수안 | 문제 정의 및 요구사항 분석, 선행 연구 조사, 보고서 작성 |
| 이하은 | 프로젝트 초기 설계, 선행 연구 조사, 보고서 작성 |
| 최시안 | 시스템 구현 및 개발, 보고서 작성 |
