"""
RAGAS evaluation utilities for the product_assistant project.

Goals:
- Safe to import: NO ModelLoader / LLM / Embeddings initialization at import-time.
- Lazy init: initialize only when an evaluation function is actually called.
- Async-first: exposes async evaluation functions that return float scores.
- Optional sync wrappers for convenience.

Requirements:
- ragas
- langchain (your LLM/embeddings are loaded via ModelLoader)
- grpc.experimental.aio (only if your environment needs grpc aio init)
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

import grpc.experimental.aio as grpc_aio

from product_assistant.utils.model_loader import ModelLoader

from ragas import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import LLMContextPrecisionWithoutReference, ResponseRelevancy


# ---------------------------------------------------------------------
# Safe, import-time initialization (no model loading)
# ---------------------------------------------------------------------
# This is generally safe to do at import time and avoids grpc warnings in some envs.
# If it causes issues in your environment, move it into _ensure_evaluators().
grpc_aio.init_grpc_aio()

_model_loader: Optional[ModelLoader] = None
_llm = None
_embeddings = None
_evaluator_llm: Optional[LangchainLLMWrapper] = None
_evaluator_embeddings: Optional[LangchainEmbeddingsWrapper] = None


def _ensure_evaluators() -> None:
    """
    Lazily initialize ModelLoader, LLM, Embeddings, and RAGAS wrappers.

    This prevents your entire app from crashing at import time if config.yaml is missing.
    Evaluation will only require config once you actually call evaluate_*.
    """
    global _model_loader, _llm, _embeddings, _evaluator_llm, _evaluator_embeddings

    if _evaluator_llm is not None and _evaluator_embeddings is not None:
        return

    _model_loader = ModelLoader()
    _llm = _model_loader.load_llm()
    _embeddings = _model_loader.load_embeddings()

    _evaluator_llm = LangchainLLMWrapper(_llm)
    _evaluator_embeddings = LangchainEmbeddingsWrapper(_embeddings)


def _as_retrieved_context_strings(retrieved_context: List[str]) -> List[str]:
    """
    Ensure retrieved contexts are strings (RAGAS expects List[str]).
    """
    return [str(x) for x in (retrieved_context or [])]


# ---------------------------------------------------------------------
# Async evaluation functions
# ---------------------------------------------------------------------
async def evaluate_context_precision(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    """
    LLMContextPrecisionWithoutReference:
    Measures how much of the retrieved context is actually useful/relevant for the answer.
    """
    _ensure_evaluators()

    sample = SingleTurnSample(
        user_input=query,
        response=response,
        retrieved_contexts=_as_retrieved_context_strings(retrieved_context),
    )

    scorer = LLMContextPrecisionWithoutReference(llm=_evaluator_llm)  # type: ignore[arg-type]
    return await scorer.single_turn_ascore(sample)


async def evaluate_response_relevancy(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    """
    ResponseRelevancy:
    Measures if the response is relevant to the query, using LLM + embeddings.
    """
    _ensure_evaluators()

    sample = SingleTurnSample(
        user_input=query,
        response=response,
        retrieved_contexts=_as_retrieved_context_strings(retrieved_context),
    )

    scorer = ResponseRelevancy(
        llm=_evaluator_llm,  # type: ignore[arg-type]
        embeddings=_evaluator_embeddings,  # type: ignore[arg-type]
    )
    return await scorer.single_turn_ascore(sample)


# ---------------------------------------------------------------------
# Optional sync wrappers (handy in non-async code)
# ---------------------------------------------------------------------
def evaluate_context_precision_sync(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    return asyncio.run(evaluate_context_precision(query, response, retrieved_context))


def evaluate_response_relevancy_sync(
    query: str,
    response: str,
    retrieved_context: List[str],
) -> float:
    return asyncio.run(evaluate_response_relevancy(query, response, retrieved_context))


# ---------------------------------------------------------------------
# CLI execution (ONLY place asyncio.run is allowed in this module)
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
