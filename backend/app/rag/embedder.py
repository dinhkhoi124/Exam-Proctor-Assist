import faiss
import pickle
import json
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from rank_bm25 import BM25Okapi
import re
import unicodedata
from typing import List, Tuple

from app.core.config import EMBEDDING_DEVICE

logger = logging.getLogger(__name__)

# Model này rất tốt cho tiếng Việt
MODEL_NAME = "intfloat/multilingual-e5-base"

class VectorStore:
    def __init__(self, dim=768):
        # Load model một lần duy nhất
        self.model = SentenceTransformer(MODEL_NAME, device=EMBEDDING_DEVICE)
        # Sử dụng IndexFlatIP cho Inner Product (tương đồng Cosine khi đã normalize)
        self.index = faiss.IndexFlatIP(dim)
        self.metadata = []

    def add(self, texts, metadatas):
        # QUAN TRỌNG: Với E5, tài liệu lưu vào phải có prefix "passage: "
        embeddings = self.model.encode(
            ["passage: " + t for t in texts],
            normalize_embeddings=True,
            show_progress_bar=True
        )
        self.index.add(np.array(embeddings).astype("float32"))
        self.metadata.extend(metadatas)

    def save(self, folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        # Thống nhất tên file với rag_service.py
        faiss.write_index(self.index, os.path.join(folder_path, "index.faiss"))
        
        # Lưu metadata dạng JSON để an toàn hơn pickle và dễ kiểm tra nội dung
        meta_path = os.path.join(folder_path, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=4)

    def load(self, folder_path):
        index_path = os.path.join(folder_path, "index.faiss")
        meta_path = os.path.join(folder_path, "metadata.json")
        
        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(index_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            logger.warning("Vector-store data was not found at %s", folder_path)

    def search(self, query, top_k=6): # Tăng top_k để có không gian cho retriever lọc trùng
        # Câu hỏi phải có prefix "query: "
        q_emb = self.model.encode(
            ["query: " + query],
            normalize_embeddings=True
        )
        scores, idxs = self.index.search(np.array(q_emb).astype("float32"), top_k)

        results = []
        for score, i in zip(scores[0], idxs[0]):
            if i != -1 and i < len(self.metadata):
                item = self.metadata[i].copy()
                item["index"] = int(i)
                item["dense_score"] = float(score)
                results.append(item)

        return results


class BM25Retriever:
    """BM25-based lexical search cho tiếng Việt"""
    
    def __init__(self):
        self.bm25 = None
        self.corpus = []
    
    def _tokenize_vietnamese(self, text: str) -> List[str]:
        """Combine Vietnamese phrases, exact lexical terms and accent folding.

        Prefixing token channels prevents accidental double counting while
        retaining exact error codes such as SEB-101 and FU-Exam.
        """
        normalized = unicodedata.normalize("NFC", text or "").casefold()
        tokens: List[str] = []

        try:
            from underthesea import word_tokenize

            segmented = word_tokenize(normalized)
            tokens.extend(
                f"seg:{re.sub(r'\s+', '_', token.strip())}"
                for token in segmented
                if len(token.strip()) > 1
            )
        except ImportError:
            pass

        lexical_tokens = re.findall(
            r"\w+(?:[-_.]\w+)*",
            normalized,
            flags=re.UNICODE,
        )
        tokens.extend(f"raw:{token}" for token in lexical_tokens if len(token) > 1)

        accent_folded = "".join(
            character
            for character in unicodedata.normalize("NFD", normalized)
            if unicodedata.category(character) != "Mn"
        ).replace("đ", "d")
        tokens.extend(
            f"fold:{token}"
            for token in re.findall(r"\w+(?:[-_.]\w+)*", accent_folded, re.UNICODE)
            if len(token) > 1
        )
        return tokens
    
    def build(self, texts: List[str]):
        """Build BM25 index"""
        tokenized = [self._tokenize_vietnamese(t) for t in texts]
        self.bm25 = BM25Okapi(tokenized)
        self.corpus = texts
    
    def search(self, query: str, top_k: int = 15) -> List[Tuple[int, float]]:
        """Search using BM25"""
        if self.bm25 is None:
            return []
        query_tokens = self._tokenize_vietnamese(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]
    
    def save(self, folder_path: str):
        import pickle
        os.makedirs(folder_path, exist_ok=True)
        with open(os.path.join(folder_path, "bm25.pkl"), "wb") as f:
            pickle.dump(self.bm25, f)
        with open(os.path.join(folder_path, "bm25_corpus.json"), "w", encoding="utf-8") as f:
            json.dump(self.corpus, f, ensure_ascii=False)
    
    def load(self, folder_path: str):
        import pickle
        bm25_path = os.path.join(folder_path, "bm25.pkl")
        corpus_path = os.path.join(folder_path, "bm25_corpus.json")
        if os.path.exists(bm25_path) and os.path.exists(corpus_path):
            with open(bm25_path, "rb") as f:
                self.bm25 = pickle.load(f)
            with open(corpus_path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)
