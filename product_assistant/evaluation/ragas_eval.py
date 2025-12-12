import asyncio
from typing import List

import grpc.experimental.aio as grpc_aio
from product_assistant.utils.model_loader import ModelLoader

from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import (
    LLMContextPrecisionWithoutReference,
    ResponseRelevancy,
)

# ---------------------------------------------------------------------
# One-time initialization
# ---------------------------------------------------------------------
grpc_aio.init_grpc_aio()

model_loader = ModelLoader()

_llm = model_loader.load_llm()
_embeddings = model_loader.load_embeddings()

_evaluator_llm = LangchainLLMWrapper(_llm)
_evaluator_embeddings = LangchainEmbeddingsWrapper(_embeddings)


# ---------------------------------------------------------------------
# Async evaluation functions
# ---------------------------------------------------------------------
async def evaluate_context_precision(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    sample = SingleTurnSample(
    user_input=query,
    response=response,
    retrieved_contexts=retrieved_context,
)
    

    scorer = LLMContextPrecisionWithoutReference(
        llm=_evaluator_llm
    )

    return await scorer.single_turn_ascore(sample)


async def evaluate_response_relevancy(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    sample = SingleTurnSample(
    user_input=query,
    response=response,
    retrieved_contexts=retrieved_context,
)

    

    scorer = ResponseRelevancy(
        llm=_evaluator_llm,
        embeddings=_evaluator_embeddings,
    )

    return await scorer.single_turn_ascore(sample)


# ---------------------------------------------------------------------
# CLI execution (ONLY place asyncio.run is allowed)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    async def main():
        precision = await evaluate_context_precision(
            query="What is RAG?",
            response="RAG retrieves documents to ground LLM answers.",
            retrieved_context=[
                "Retrieval-Augmented Generation combines retrieval with generation."
            ],
        )

        relevancy = await evaluate_response_relevancy(
            query="What is RAG?",
            response="RAG retrieves documents to ground LLM answers.",
            retrieved_context=[
                "Retrieval-Augmented Generation combines retrieval with generation."
            ],
        )

        print("Context precision:", precision)
        print("Response relevancy:", relevancy)

    asyncio.run(main())
