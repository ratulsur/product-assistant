from mcp.server.fastmcp import FastMCP
from product_assistant.retriever.retrieval import Retriever
from langchain_community.tools import DuckDuckGoSearchRun

mcp = FastMCP("hybrid search")

retriever_obj = Retriever()
retriever = retriever_obj.load_retriever()

duckduckgo = DuckDuckGoSearchRun()

def format_docs(docs)->str:
    """
    format retriever docs into readable context
    """
    if not docs:
        return ""
    formatted_chunks = []

    for d in docs:
        meta = d.metadata or {}
        formatted = (
            f"title: {meta.get('product_title', 'N/A')}\n"
            f"price: {meta.get('price', 'N/A')}/n"
            f"Rating: {meta.get('rating', 'N/A')}/n"
            f"Review: {meta.get('Review', 'N/A')}/n"
        )
        formatted_chunks.append(formatted)
    