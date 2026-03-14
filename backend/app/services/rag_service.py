import os
import faiss
import numpy as np
from openai import OpenAI
from app.core.config import OPENAI_API_KEY, VECTOR_STORE_DIR

client = OpenAI(api_key=OPENAI_API_KEY)
EMBEDDING_MODEL = "text-embedding-3-large"

class RAGService:
    def __init__(self):
        index_path = os.path.join(VECTOR_STORE_DIR, "index.faiss")
        text_path = os.path.join(VECTOR_STORE_DIR, "texts.txt")

        if not os.path.exists(index_path):
            self.index = None
            self.texts = []
            return

        self.index = faiss.read_index(index_path)
        with open(text_path, "r", encoding="utf-8") as f:
            self.texts = f.readlines()

    def retrieve(self, query: str, top_k: int = 3):
        if self.index is None:
            return []

        emb = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query
        ).data[0].embedding

        D, I = self.index.search(
            np.array([emb]).astype("float32"),
            top_k
        )

        return [self.texts[i] for i in I[0] if i < len(self.texts)]
