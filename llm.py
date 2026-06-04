"""
llm.py — OpenAI chat client and a small call_llm helper.

The client is created lazily (on first use) so importing this module never
requires an API key. Set the key via the OPENAI_API_KEY environment variable:

    export OPENAI_API_KEY="sk-..."

Usage:
    from llm import call_llm
    answer = call_llm("Say hi in Korean.")
"""

from functools import lru_cache

CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-large"   # OpenAI embeddings (reference; matcher uses e5)


@lru_cache(maxsize=1)
def _client():
    """Create the OpenAI client once, reusing it on subsequent calls."""
    from openai import OpenAI
    return OpenAI()  # reads OPENAI_API_KEY from the environment


def call_llm(prompt: str, system: str = "",
             model: str = CHAT_MODEL,
             temperature: float = 0.0,
             max_tokens: int = 10000) -> str:
    """Send a single prompt to the chat model and return the text reply.

    Warns if the response was cut off by the max_tokens limit.
    """
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    r = _client().chat.completions.create(
        model=model, messages=msgs,
        temperature=temperature, max_tokens=max_tokens,
    )
    if r.choices[0].finish_reason == "length":
        print("⚠️ call_llm: response hit max_tokens and was truncated — raise max_tokens.")
    return r.choices[0].message.content.strip()
