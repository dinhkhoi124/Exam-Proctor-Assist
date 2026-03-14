import faiss
import pickle
import json # Nên dùng JSON cho metadata để dễ debug
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# Model này rất tốt cho tiếng Việt
MODEL_NAME = "intfloat/multilingual-e5-base"

class VectorStore:
    def __init__(self, dim=768):
        # Load model một lần duy nhất
        self.model = SentenceTransformer(MODEL_NAME)
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
            print(f"⚠ Không tìm thấy dữ liệu tại {folder_path}")

    def search(self, query, top_k=6): # Tăng top_k để có không gian cho retriever lọc trùng
        # Câu hỏi phải có prefix "query: "
        q_emb = self.model.encode(
            ["query: " + query],
            normalize_embeddings=True
        )
        scores, idxs = self.index.search(np.array(q_emb).astype("float32"), top_k)

        results = []
        for i in idxs[0]:
            if i != -1 and i < len(self.metadata):
                results.append(self.metadata[i])

        return results