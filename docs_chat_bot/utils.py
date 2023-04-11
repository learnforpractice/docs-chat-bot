import numpy as np
import openai
import tiktoken
from pymixin import log

logger = log.get_logger(__name__)
logger.addHandler(log.handler)

EMBEDDING_MODEL = "text-embedding-ada-002"
max_prompt_token = 3000

gpt_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

def count_tokens(message) -> int:
    tokens = gpt_encoding.encode(message)
    return len(tokens)

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> list[float]:
    result = openai.Embedding.create(
      model=model,
      input=text,
      timeout=10
    )
    return result["data"][0]["embedding"]


def vector_similarity(x: list[float], y: list[float]) -> float:
    """
    Returns the similarity between two vectors.
    
    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))

embeddings = None

def top_n_similarity(query_embedding, embeddings, n):
    if n > len(embeddings):
        raise Exception("n is larger than the length of the list")

    top_n = [(float('-inf'), None)] * n

    for key in embeddings:
        doc_embedding = embeddings[key]
        similarity = vector_similarity(query_embedding, doc_embedding)
        min_value = min(top_n)
        min_index = top_n.index(min_value)

        if similarity > min_value[0]:
            top_n[min_index] = (similarity, key)

    return sorted(top_n, reverse=True)
