"""음식 목록 중 사용자 입력과 의미적으로 가장 가까운 음식을 임베딩으로 찾는다.

OpenAI 임베딩 API로 각 음식과 사용자 입력을 벡터로 바꾼 뒤,
코사인 유사도가 가장 높은 음식을 반환한다.

사용 예:
    matcher = FoodMatcher(["김치찌개", "스파게티", "마르게리타 피자"])
    matcher.match("파스타")           # -> [("스파게티", 0.83)]
    matcher.match("피자", top_k=3)    # 상위 3개
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np

# text-embedding-3-small: 저렴하고 품질이 좋아 기본값으로 적합.
# 더 높은 정확도가 필요하면 "text-embedding-3-large" 로 바꾼다.
EMBED_MODEL = "text-embedding-3-small"
CACHE_DIR = ".embed_cache"


@lru_cache(maxsize=1)
def _client():
    """OpenAI 클라이언트를 최초 사용 시점에 한 번만 생성한다.

    모듈을 import 하는 것만으로 API 키가 필요해지지 않도록 지연 생성한다.
    """
    from openai import OpenAI
    return OpenAI()  # OPENAI_API_KEY 환경변수를 자동으로 읽는다.


def embed(texts, model=EMBED_MODEL, batch_size=512):
    """문자열(또는 리스트)을 L2 정규화된 임베딩 행렬로 변환한다.

    반환: np.ndarray, shape = (len(texts), dim)
    미리 정규화해 두면 코사인 유사도를 단순 내적으로 계산할 수 있다.
    음식 목록이 커도 batch_size 단위로 나눠 호출한다.
    """
    if isinstance(texts, str):
        texts = [texts]

    vectors = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        resp = _client().embeddings.create(model=model, input=chunk)
        vectors.extend(item.embedding for item in resp.data)

    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


class FoodMatcher:
    """음식 목록의 임베딩을 보관하고, 입력과 가장 가까운 음식을 찾는다.

    embed_fn 을 주입할 수 있어, 실제 API 없이도(테스트용 가짜 임베더 등) 동작시킬 수 있다.
    """

    def __init__(self, foods, model=EMBED_MODEL, embed_fn=embed, use_cache=True):
        self.foods = list(foods)
        self.model = model
        self.embed_fn = embed_fn
        # (N, dim) 정규화된 음식 임베딩 행렬
        self.matrix = self._load_or_embed(use_cache)

    def _cache_path(self):
        # 음식 목록이나 모델이 바뀌면 캐시도 달라지도록 내용 해시로 파일명을 만든다.
        signature = self.model + "\n" + "\n".join(self.foods)
        digest = hashlib.md5(signature.encode("utf-8")).hexdigest()[:16]
        return os.path.join(CACHE_DIR, f"foods_{digest}.npy")

    def _load_or_embed(self, use_cache):
        if not use_cache:
            return self.embed_fn(self.foods, self.model)

        path = self._cache_path()
        if os.path.exists(path):          # 이미 임베딩해 둔 적이 있으면 재사용 (비용/지연 절약)
            return np.load(path)

        matrix = self.embed_fn(self.foods, self.model)
        os.makedirs(CACHE_DIR, exist_ok=True)
        np.save(path, matrix)
        return matrix

    def match(self, query, top_k=1):
        """query 와 가장 가까운 음식 top_k개를 [(음식, 유사도), ...] 로 반환한다.

        유사도는 코사인 유사도(-1~1, 클수록 비슷함)이다.
        반환된 점수가 너무 낮으면(예: 0.3 미만) "목록에 없는 음식"으로 처리할 수 있다.
        """
        q = self.embed_fn(query, self.model)[0]   # (dim,), 정규화됨
        sims = self.matrix @ q                      # 정규화돼 있으므로 내적 = 코사인 유사도
        order = np.argsort(-sims)[:top_k]           # 유사도 내림차순 상위 top_k
        return [(self.foods[i], float(sims[i])) for i in order]


if __name__ == "__main__":
    foods = [
        "김치찌개", "된장찌개", "비빔밥", "삼겹살",
        "스파게티", "마르게리타 피자", "후라이드 치킨", "초밥",
    ]
    matcher = FoodMatcher(foods)

    for query in ["파스타", "피자", "닭튀김", "회"]:
        food, score = matcher.match(query)[0]
        print(f"{query:8} -> {food}  (유사도 {score:.3f})")
