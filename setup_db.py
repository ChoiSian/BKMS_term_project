"""psycopg2 연결(conn) 위에 임시 작업용 DB(테이블)를 구축하는 예제.

핵심 흐름:  conn.cursor() 로 SQL 실행  →  conn.commit() 으로 확정.
psycopg2 는 기본적으로 트랜잭션을 자동 시작하므로, commit 하지 않으면
연결을 닫을 때 모든 변경이 롤백된다(가장 흔한 실수).

세 가지 "임시 DB" 패턴을 보여준다.
  1) create_schema       : DROP IF EXISTS + CREATE  (재실행 가능한 개발용 스키마)
  2) create_temp_tables  : CREATE TEMP TABLE         (연결 종료 시 자동 삭제)
  3) build()             : 앞서 만든 parse_record 결과를 그대로 적재
"""

import psycopg2
from psycopg2.extras import execute_values

from parse_record import parse_record


def get_connection():
    # 사용자가 준 스니펫과 동일한 연결
    return psycopg2.connect(
        host="localhost", dbname="textbook",
        user="postgres", password="dbclass",
    )


# 1) 재실행 가능한 개발용 스키마 ------------------------------------------------
#    같은 스크립트를 여러 번 돌려도 깨끗하게 다시 만들어진다.
SCHEMA_SQL = """
DROP TABLE IF EXISTS user_menus;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS foods;

CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    age           INTEGER,
    gender        CHAR(1),          -- 'F' / 'M'
    hypertension  BOOLEAN
);

CREATE TABLE foods (
    food_id  SERIAL PRIMARY KEY,
    name     TEXT UNIQUE NOT NULL
);

CREATE TABLE user_menus (           -- 사용자 ↔ 음식 (N:M 연결 테이블)
    user_id  INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    food_id  INTEGER REFERENCES foods(food_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, food_id)
);
"""


def create_schema(conn):
    with conn.cursor() as cur:        # with 블록이 끝나면 커서를 자동으로 닫는다
        cur.execute(SCHEMA_SQL)       # 여러 문장을 한 번에 실행 가능
    conn.commit()                     # ★ 반드시 commit 해야 실제 반영된다


# 2) 세션 한정 '진짜' 임시 테이블 -----------------------------------------------
#    이 연결에서만 보이고, 연결이 끊기면 자동으로 사라진다(직접 DROP 불필요).
def create_temp_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TEMP TABLE tmp_candidates (
                name        TEXT,
                similarity  REAL
            );
        """)
    conn.commit()


# 3) 데이터 적재 ----------------------------------------------------------------
def seed(conn, age, gender, hypertension, menu, foods):
    with conn.cursor() as cur:
        # (a) 단일 INSERT — 값은 %s 플레이스홀더로! (f-string 금지: SQL 인젝션)
        #     RETURNING 으로 방금 생성된 PK 를 돌려받는다.
        cur.execute(
            "INSERT INTO users (age, gender, hypertension) "
            "VALUES (%s, %s, %s) RETURNING user_id",
            (age, gender, hypertension),
        )
        user_id = cur.fetchone()[0]

        # (b) 다건 INSERT — execute_values 가 executemany 보다 훨씬 빠르다.
        #     ON CONFLICT 로 이미 있는 음식은 건너뛴다.
        execute_values(
            cur,
            "INSERT INTO foods (name) VALUES %s ON CONFLICT (name) DO NOTHING",
            [(name,) for name in foods],
        )

        # (c) 사용자가 고른 메뉴를 이름으로 찾아 연결 (= ANY(%s): 리스트→배열 자동 변환)
        cur.execute(
            "INSERT INTO user_menus (user_id, food_id) "
            "SELECT %s, food_id FROM foods WHERE name = ANY(%s)",
            (user_id, menu),
        )
    conn.commit()
    return user_id


# 적재 결과 확인 ----------------------------------------------------------------
def show(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT u.user_id, u.age, u.gender, u.hypertension,
                   array_agg(f.name) AS menu
            FROM users u
            LEFT JOIN user_menus m ON m.user_id = u.user_id
            LEFT JOIN foods      f ON f.food_id = m.food_id
            GROUP BY u.user_id
            ORDER BY u.user_id
        """)
        return cur.fetchall()


if __name__ == "__main__":
    # 앞서 만든 parser 로 한 줄짜리 레코드를 딕셔너리로 변환해 그대로 적재
    rec = parse_record('나이 : 20, 성별 : F, 고혈압 : T, 음식 메뉴 : ["식전 빵", "파스타"]')
    foods = ["식전 빵", "파스타", "김치찌개", "스파게티", "마르게리타 피자"]

    conn = get_connection()
    try:
        create_schema(conn)
        user_id = seed(
            conn,
            age=rec["나이"], gender=rec["성별"],
            hypertension=rec["고혈압"], menu=rec["음식 메뉴"],
            foods=foods,
        )
        print(f"inserted user_id = {user_id}")
        for row in show(conn):
            print(row)
    finally:
        conn.close()          # 연결 종료 (TEMP 테이블이 있었다면 여기서 자동 삭제)
