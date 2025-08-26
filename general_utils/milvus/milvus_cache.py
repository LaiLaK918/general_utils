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

from ..utils.log_common import build_logger

logger = build_logger("milvus_cache")


class MilvusCache:
    def __init__(
        self,
        collection_name="agent_cache",
        host="localhost",
        port="19530",
        embedding_model="text-embedding-3-small",
        embedding_dim=1536,
    ):
        connections.connect("default", host=host, port=port)
        self.collection_name = collection_name

        # OpenAI API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")
        self.client = openai.OpenAI(api_key=api_key)

        # choose embedding model
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

        if not utility.has_collection(collection_name):
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.embedding_dim,
                    is_primary=False,
                ),
                FieldSchema(
                    name="question",
                    dtype=DataType.VARCHAR,
                    max_length=512,
                    is_primary=False,
                ),
                FieldSchema(name="answer", dtype=DataType.VARCHAR, max_length=2048),
            ]
            schema = CollectionSchema(fields, "QA cache")
            Collection(collection_name, schema)

        self.collection = Collection(collection_name)
        self.collection.load()  # <-- ensure data is in memory

    def _embed(self, text: str):
        resp = self.client.embeddings.create(model=self.embedding_model, input=text)
        return resp.data[0].embedding

    def search(self, question, threshold=0.9):
        embedding = [self._embed(question)]
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
            logger.info("✅ Insert success")
        else:
            logger.info("❌ Insert failed")
