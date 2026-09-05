import hashlib
import math
import re

VECTOR_SIZE = 384


def embed(text: str) -> list[float]:
    """Stable local embedding for development; replace with a biomedical model in deployment."""
    vector = [0.0] * VECTOR_SIZE
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        if len(term) < 3:
            continue
        digest = hashlib.sha256(term.encode()).digest()
        index = int.from_bytes(digest[:2], "big") % VECTOR_SIZE
        vector[index] += -1.0 if digest[2] & 1 else 1.0
    magnitude = math.sqrt(sum(value * value for value in vector))
    return [value / magnitude for value in vector] if magnitude else vector
