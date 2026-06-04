"""psycopg2 연결을 감싸 SQL 조회/실행을 간단하게 해주는 wrapper.

사용 예:
    db = DB(host="localhost", dbname="textbook",
            user="postgres", password="dbclass")

    db.query_one("SELECT * FROM 영양성분db WHERE 식품명 = %s", ("스파게티",))
    # -> {'식품명': '스파게티', '에너지': 371.0, '단백질': 13.0, ...}   (dict 로 반환)

핵심:
- RealDictCursor 를 써서 결과를 (튜플이 아니라) 컬럼명 dict 로 받는다.
- 값은 항상 %s 플레이스홀더 + params 로 전달 → SQL 인젝션 방지.
- with 문으로 자동 정리(정상 종료 시 commit, 예외 시 rollback).
"""

import psycopg2
from psycopg2.extras import RealDictCursor


class DB:
    def __init__(self, **conn_params):
        self.conn = psycopg2.connect(**conn_params)

    # ---- 읽기 (SELECT) ----------------------------------------------------
    def query(self, sql, params=None):
        """여러 행을 dict 리스트로 반환."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql, params=None):
        """첫 행을 dict 로 반환 (결과 없으면 None)."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    # ---- 쓰기 (INSERT / UPDATE / DELETE) ----------------------------------
    def execute(self, sql, params=None):
        """실행 후 commit, 영향받은 행 수 반환."""
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            self.conn.commit()
            return cur.rowcount

    def executemany(self, sql, rows):
        """여러 행을 한 번에 실행 후 commit."""
        with self.conn.cursor() as cur:
            cur.executemany(sql, rows)
            self.conn.commit()
            return cur.rowcount

    # ---- 정리 / with 문 지원 ----------------------------------------------
    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.close()


if __name__ == "__main__":
    db = DB(host="localhost", dbname="textbook",
            user="postgres", password="dbclass")

    # ① 식품명으로 1건 조회 (값은 %s 파라미터로! f-string 금지)
    row = db.query_one(
        "SELECT * FROM 영양성분db WHERE 식품명 = %s", ("스파게티",))
    print("query_one:", row)

    # ② 여러 식품명을 한 번에 조회 (파이썬 리스트 → = ANY(%s))
    rows = db.query(
        "SELECT 식품명, 에너지, 나트륨 FROM 영양성분db WHERE 식품명 = ANY(%s)",
        (["토마토 파스타", "크림 파스타"],))
    print("query(ANY):", rows)

    # ③ 조건 필터 — 예: 나트륨 낮은 음식 추천
    low_sodium = db.query(
        "SELECT 식품명, 나트륨 FROM 영양성분db WHERE 나트륨 < %s ORDER BY 나트륨",
        (500,))
    print("저나트륨:", low_sodium)

    db.close()
