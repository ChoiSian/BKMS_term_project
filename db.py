"""psycopg2 연결을 감싸 SQL 조회/실행을 간단하게 해주는 wrapper.

사용 예:
    db = DB(host="localhost", dbname="textbook",
            user="postgres", password="dbclass")        # init 시 스키마 자동 생성

    db.query_one("SELECT * FROM 영양성분db WHERE 식품명 = %s", ("스파게티",))
    # -> {'식품명': '스파게티', '에너지': 371.0, ...}   (dict 로 반환)

핵심:
- __init__ 에서 프로젝트 스키마(영양성분DB, 영양소조건)를 초기화한다.
    · 기본은 CREATE TABLE IF NOT EXISTS → 이미 있으면 그대로 두고 데이터 보존
    · reset=True 면 DROP 후 다시 생성 (깨끗한 초기화)
    · init=False 면 스키마를 건드리지 않고 연결만 한다
- RealDictCursor 로 결과를 (튜플이 아니라) 컬럼명 dict 로 받는다.
- 값은 항상 %s 플레이스홀더 + params 로 전달 → SQL 인젝션 방지.
- with 문으로 자동 정리(정상 종료 시 commit, 예외 시 rollback).
"""

import psycopg2
from psycopg2.extras import RealDictCursor


class DB:
    # init 시 생성할 프로젝트 스키마 (필요하면 여기에 테이블을 추가하면 된다)
    SCHEMA = [
        """CREATE TABLE IF NOT EXISTS 영양성분DB (
            식품명   VARCHAR(50) PRIMARY KEY,
            에너지   FLOAT,
            단백질   FLOAT,
            지방     FLOAT,
            탄수화물 FLOAT,
            나트륨   FLOAT
        )""",
        """CREATE TABLE IF NOT EXISTS 영양소조건 (
            성별        VARCHAR(50),
            연령대_하한  INT,
            연령대_상한  INT,
            에너지      FLOAT,
            단백질      FLOAT,
            지방        FLOAT,
            탄수화물    FLOAT,
            나트륨      FLOAT
        )""",
    ]
    TABLES = ["영양성분DB", "영양소조건"]

    def __init__(self, init=True, reset=False, **conn_params):
        # 예: DB(host="localhost", dbname="textbook", user="postgres", password="dbclass")
        self.conn = psycopg2.connect(**conn_params)
        if init or reset:
            self.init_db(reset=reset)

    # ---- 스키마 초기화 ----------------------------------------------------
    def init_db(self, reset=False):
        """프로젝트 스키마를 초기화한다.

        reset=False : CREATE TABLE IF NOT EXISTS (기존 데이터 보존)
        reset=True  : 기존 테이블을 DROP 후 새로 생성 (전체 초기화)
        """
        with self.conn.cursor() as cur:
            if reset:
                for table in self.TABLES:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            for ddl in self.SCHEMA:
                cur.execute(ddl)
        self.conn.commit()

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
    # reset=True 로 테이블을 깨끗이 새로 만든다 (init 동작 확인)
    db = DB(host="localhost", dbname="textbook",
            user="postgres", password="dbclass", reset=True)

    # 샘플 데이터 적재
    db.executemany(
        "INSERT INTO 영양성분db VALUES (%s,%s,%s,%s,%s,%s)",
        [("스파게티", 371, 13, 1.5, 75, 6),
         ("크림 파스타", 200, 6, 11, 20, 500)])

    # 식품명으로 1건 조회 (값은 %s 파라미터로! f-string 금지)
    print("query_one:", dict(db.query_one(
        "SELECT * FROM 영양성분db WHERE 식품명 = %s", ("스파게티",))))

    # 빈 영양소조건 테이블도 init 으로 생성돼 있음
    print("영양소조건 컬럼 수:", len(db.query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = '영양소조건'")))

    db.close()
