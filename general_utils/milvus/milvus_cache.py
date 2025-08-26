import os

import openai
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)


class MilvusCache:
    def __init__(self, collection_name="agent_cache", host="localhost", port="19530"):
        connections.connect("default", host=host, port=port)
        self.collection_name = collection_name

        # OpenAI API key from environment
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        
        # choose embedding model
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536  # 3072 for -large

        if not utility.has_collection(collection_name):
            fields = [
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim, is_primary=False),
                FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=512, is_primary=True),
                FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=2048),
            ]
            schema = CollectionSchema(fields, "QA cache")
            Collection(collection_name, schema)

        self.collection = Collection(collection_name)

    def _embed(self, text: str):
        resp = openai.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return resp.data[0].embedding

    def search(self, question, threshold=0.9):
        embedding = [self._embed(question)]
        self.collection.load()   # <-- ensure data is in memory
        results = self.collection.search(
            data=embedding,
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=1,
            output_fields=["question", "answer"],
        )
        if results and results[0]:
            hit = results[0][0]
            if hit.score >= threshold:
                return hit.entity.get("answer")
        return None
    
    def add(self, question, answer):
        embedding = [self._embed(question)]
        res = self.collection.insert([embedding, [question], [answer]])
        self.collection.flush()
        if res.insert_count > 0:
            print("✅ Insert success")
        else:
            print("❌ Insert failed")
