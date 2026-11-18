import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass


_STOP_WORDS = {
    "a", "al", "algo", "como", "con", "cual", "cuales", "cuanto", "cuantos",
    "de", "del", "el", "en", "es", "esta", "este", "la", "las", "lo", "los",
    "me", "mi", "para", "por", "que", "se", "segun", "sobre", "un", "una",
    "y",
}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return [
        token for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) > 1 and token not in _STOP_WORDS
    ]


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    page: int
    similarity: float


class SleepGuideRetriever:
    def __init__(self, pages: list[str], top_k: int = 2, chunk_size: int = 700):
        if top_k < 1:
            raise ValueError("top_k debe ser mayor que cero")
        self.top_k = top_k
        self._chunks = self._split_pages(pages, chunk_size)
        self._vectors = [Counter(_tokens(chunk.text)) for chunk in self._chunks]
        self._idf = self._build_idf(self._vectors)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @staticmethod
    def _split_pages(pages: list[str], chunk_size: int) -> list[RetrievedChunk]:
        chunks = []
        sentence_pattern = re.compile(r"(?<=[.!?])\s+")
        for page_number, page in enumerate(pages, start=1):
            sentences = sentence_pattern.split(" ".join(page.split()))
            current = ""
            for sentence in sentences:
                if not sentence:
                    continue
                if current and len(current) + len(sentence) + 1 > chunk_size:
                    chunks.append(RetrievedChunk(current, page_number, 0.0))
                    current = ""
                current = f"{current} {sentence}".strip()
            if current:
                chunks.append(RetrievedChunk(current, page_number, 0.0))
        return chunks

    @staticmethod
    def _build_idf(vectors: list[Counter[str]]) -> dict[str, float]:
        document_frequency = Counter(
            term for vector in vectors for term in vector
        )
        document_count = len(vectors)
        return {
            term: math.log((document_count + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        query = Counter(_tokens(question))
        if not query or not self._chunks:
            return []

        query_vector = {
            term: count * self._idf.get(term, 1.0)
            for term, count in query.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
        if query_norm == 0:
            return []

        scored = []
        for chunk, vector in zip(self._chunks, self._vectors):
            vector_weights = {
                term: count * self._idf[term]
                for term, count in vector.items()
            }
            vector_norm = math.sqrt(
                sum(weight * weight for weight in vector_weights.values())
            )
            dot_product = sum(
                weight * vector_weights.get(term, 0.0)
                for term, weight in query_vector.items()
            )
            similarity = dot_product / (query_norm * vector_norm) if vector_norm else 0
            scored.append(
                RetrievedChunk(chunk.text, chunk.page, round(similarity * 100, 2))
            )

        scored.sort(key=lambda chunk: chunk.similarity, reverse=True)
        return [chunk for chunk in scored[:self.top_k] if chunk.similarity > 0]
