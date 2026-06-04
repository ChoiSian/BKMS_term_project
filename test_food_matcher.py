"""food_matcher 의 유사도 로직 검증 (OpenAI API 없이 가짜 임베더로 테스트).

실제 임베딩 대신, 의미가 비슷한 단어가 같은 방향을 향하도록 직접 만든
벡터를 주입해 match() 가 가장 가까운 음식을 고르는지 확인한다.
"""

import numpy as np

from food_matcher import FoodMatcher

# 단어별 고정 벡터. "파스타"는 "스파게티"와 거의 같은 방향이 되도록 설계.
FAKE_VECTORS = {
    "스파게티": [1.0, 0.0, 0.0],
    "마르게리타 피자": [0.0, 1.0, 0.0],
    "김치찌개": [0.0, 0.0, 1.0],
    "파스타": [0.95, 0.05, 0.0],
    "피자": [0.05, 0.95, 0.0],
}


def fake_embed(texts, model=None):
    if isinstance(texts, str):
        texts = [texts]
    vecs = np.array([FAKE_VECTORS[t] for t in texts], dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def test_nearest_match():
    matcher = FoodMatcher(
        ["스파게티", "마르게리타 피자", "김치찌개"],
        embed_fn=fake_embed,
        use_cache=False,
    )
    assert matcher.match("파스타")[0][0] == "스파게티"
    assert matcher.match("피자")[0][0] == "마르게리타 피자"


def test_top_k_order():
    matcher = FoodMatcher(
        ["스파게티", "마르게리타 피자", "김치찌개"],
        embed_fn=fake_embed,
        use_cache=False,
    )
    ranked = matcher.match("파스타", top_k=3)
    foods = [food for food, _ in ranked]
    assert foods[0] == "스파게티"            # 가장 가까움
    assert foods[-1] == "김치찌개"           # 가장 멂
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)  # 유사도 내림차순


if __name__ == "__main__":
    test_nearest_match()
    test_top_k_order()
    print("모든 테스트 통과 ✅")

    # 데모: 가짜 임베더로 실제 match 결과 출력
    matcher = FoodMatcher(
        ["스파게티", "마르게리타 피자", "김치찌개"],
        embed_fn=fake_embed,
        use_cache=False,
    )
    print(matcher.match("파스타", top_k=3))
