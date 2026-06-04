"""
llm.py — OpenAI chat client and a small call_llm helper.
"""

from functools import lru_cache

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-large"   


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI
    return OpenAI()  # reads OPENAI_API_KEY from the environment


def call_llm(prompt: str, system: str = "",
             model: str = CHAT_MODEL,
             temperature: float = 0.0,
             max_tokens: int = 10000) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    r = _client().chat.completions.create(
        model=model, messages=msgs,
        temperature=temperature, max_tokens=max_tokens,
    )
    return r.choices[0].message.content.strip()
