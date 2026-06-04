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
- 쿼리가 실패하면 자동으로 rollback 한다 → 다음 쿼리가 'transaction is
  aborted' 로 막히지 않음 (노트북에서 셀 반복 실행 시 특히 중요).
- with 문으로 자동 정리(정상 종료 시 commit, 예외 시 rollback).
"""

from contextlib import contextmanager

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
            나트륨      FLOAT,
            -- (성별, 연령대) 조합당 1행이어야 한다 → 중복 INSERT 방지
            PRIMARY KEY (성별, 연령대_하한, 연령대_상한)
        )""",
    ]
    TABLES = ["영양성분DB", "영양소조건"]

    def __init__(self, init=True, reset=False, **conn_params):
        # 예: DB(host="localhost", dbname="textbook", user="postgres", password="dbclass")
        self.conn = psycopg2.connect(**conn_params)
        if init or reset:
            self.init_db(reset=reset)

    @contextmanager
    def _cursor(self, commit=False, dict_rows=False):
        """커서를 열고 성공하면 (필요시) commit, 실패하면 rollback 한다.

        실패 후 rollback 을 해줘야 다음 쿼리가 'current transaction is aborted'
        로 막히지 않는다.
        """
        cur = self.conn.cursor(
            cursor_factory=RealDictCursor if dict_rows else None)
        try:
            yield cur
            if commit:
                self.conn.commit()
        except Exception:
            self.conn.rollback()   # 실패 시 트랜잭션 정리 → 다음 쿼리 가능
            raise
        finally:
            cur.close()

    # ---- 스키마 초기화 ----------------------------------------------------
    def init_db(self, reset=False):
        """프로젝트 스키마를 초기화한다.

        reset=False : CREATE TABLE IF NOT EXISTS (기존 데이터 보존)
        reset=True  : 기존 테이블을 DROP 후 새로 생성 (전체 초기화)
        """
        with self._cursor(commit=True) as cur:
            if reset:
                for table in self.TABLES:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            for ddl in self.SCHEMA:
                cur.execute(ddl)

    # ---- 읽기 (SELECT) ----------------------------------------------------
    def query(self, sql, params=None):
        """여러 행을 dict 리스트로 반환."""
        with self._cursor(dict_rows=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql, params=None):
        """첫 행을 dict 로 반환 (결과 없으면 None)."""
        with self._cursor(dict_rows=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    # ---- 쓰기 (INSERT / UPDATE / DELETE) ----------------------------------
    def execute(self, sql, params=None):
        """실행 후 commit, 영향받은 행 수 반환."""
        with self._cursor(commit=True) as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def executemany(self, sql, rows):
        """여러 행을 한 번에 실행 후 commit."""
        with self._cursor(commit=True) as cur:
            cur.executemany(sql, rows)
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

    # 이미 존재하는 테이블을 또 CREATE 하면 실패하지만, 자동 rollback 되어
    # 이후 쿼리는 정상 동작한다.
    try:
        db.execute("CREATE TABLE 영양성분DB (식품명 VARCHAR(50))")
    except psycopg2.errors.DuplicateTable:
        print("CREATE 재실행은 실패(이미 존재) — 하지만 연결은 살아있음")
    print("이후 조회 OK:", db.query_one("SELECT count(*) AS n FROM 영양성분db"))

    db.close()
