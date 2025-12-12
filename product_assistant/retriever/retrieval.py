import os
import asyncio
from dotenv import load_dotenv

from langchain_astradb import AstraDBVectorStore
from langchain.retrievers.document_compressors import LLMChainFilter
from langchain.retrievers import ContextualCompressionRetriever

from product_assistant.utils.config_loader import load_config
from product_assistant.utils.model_loader import ModelLoader

# RAGAS evaluation (import explicitly)
from product_assistant.evaluation.ragas_eval import (
    evaluate_context_precision,
    evaluate_response_relevancy,
)


class Retriever:
    def __init__(self):
        self.model_loader = ModelLoader()
        self.config = load_config()
        self._load_env_variables()

        self.vstore = None
        self.retriever_instance = None

    def _load_env_variables(self):
        """Load and validate required environment variables"""
        load_dotenv()

        required_vars = [
            "GOOGLE_API_KEY",
            "ASTRA_DB_API_ENDPOINT",
            "ASTRA_DB_APPLICATION_TOKEN",
            "ASTRA_DB_KEYSPACE",
        ]

        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {missing}")

        self.db_api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")

    def load_retriever(self):
        """Lazy-load vector store and retriever"""
        if self.vstore is None:
            collection_name = self.config["astra_db"]["collection_name"]

            self.vstore = AstraDBVectorStore(
                embedding=self.model_loader.load_embeddings(),
                collection_name=collection_name,
                api_endpoint=self.db_api_endpoint,
                token=self.db_application_token,
                namespace=self.db_keyspace,
            )

        if self.retriever_instance is None:
            top_k = self.config.get("retriever", {}).get("top_k", 3)

            base_retriever = self.vstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": top_k,
                    "fetch_k": 20,
                    "lambda_mult": 0.7,
                },
            )

            llm = self.model_loader.load_llm()
            compressor = LLMChainFilter.from_llm(llm)

            self.retriever_instance = ContextualCompressionRetriever(
                base_retriever=base_retriever,
                base_compressor=compressor,
            )

        return self.retriever_instance

    def retrieve(self, query: str):
        """Public retrieval API"""
        retriever = self.load_retriever()
        return retriever.invoke(query)


def format_docs(docs) -> list[str]:
    """Convert LangChain Documents → strings for RAGAS"""
    if not docs:
        return []

    formatted = []
    for d in docs:
        meta = d.metadata or {}
        formatted.append(
            f"Title: {meta.get('product_title', 'N/A')}\n"
            f"Price: {meta.get('price', 'N/A')}\n"
            f"Rating: {meta.get('rating', 'N/A')}\n"
            f"Reviews:\n{d.page_content.strip()}"
        )

    return formatted


# -------------------------------------------------------------------
# CLI / test runner
# -------------------------------------------------------------------
if __name__ == "__main__":

    async def main():
        user_query = "can you suggest some good smartphones under Rs 10000?"

        retriever = Retriever()
        docs = retriever.retrieve(user_query)

        retrieved_contexts = format_docs(docs)

        # Fake response (for testing only)
        response = "Some good phones under Rs 10,000 are Redmi A2, Realme Narzo, and Samsung Galaxy F04."

        context_score = await evaluate_context_precision(
            user_query, response, retrieved_contexts
        )

        relevancy_score = await evaluate_response_relevancy(
            user_query, response, retrieved_contexts
        )

        print("\n--- Evaluation Metrics ---")
        print("Context Precision:", context_score)
        print("Response Relevancy:", relevancy_score)

    asyncio.run(main())
