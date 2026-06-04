"""
food_matcher.py — Map a user's food name to the closest 식품명 in the DB.
"""

import os

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

E5_MODEL = "intfloat/multilingual-e5-large"
_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(E5_MODEL, device=_device)
    return _model


def embed_passages(names, batch_size=128):
    return _get_model().encode(
        [f"passage: {n}" for n in names],
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )


def embed_query(text):
    return _get_model().encode(
        [f"query: {text}"],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )[0]


class FoodMatcher:
    def __init__(self, foods, matrix_path=None):
        self.foods = list(foods)
        if matrix_path is not None and os.path.exists(matrix_path):
            self.matrix = pd.read_csv(matrix_path).to_numpy()   # (N, dim)
        else:
            self.matrix = embed_passages(self.foods)
        assert len(self.foods) == self.matrix.shape[0], (
            f"foods({len(self.foods)}) != matrix rows({self.matrix.shape[0]})")

    def save_matrix(self, path):
        pd.DataFrame(self.matrix).to_csv(path, index=False)

    def match(self, query, top_k=5):
        q = embed_query(query)                 # (dim,), normalized
        sims = self.matrix @ q                  # cosine sim (both normalized)
        order = np.argsort(-sims)[:top_k]
        return [(self.foods[i], float(sims[i])) for i in order]


def make_food_list(matcher, food_names):
    return [matcher.match(name)[0][0] for name in food_names]
