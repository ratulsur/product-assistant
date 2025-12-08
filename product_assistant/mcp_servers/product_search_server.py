from mcp.server.fastmcp import FastMCP
from product_assistant.retriever.retrieval import Retriever
from langchain_community.tools import DuckDuckGoSearchRun

mcp = FastMCP("hybrid search")

# Eager init (simple). If you prefer, move this into get_product_info lazily.
retriever_obj = Retriever()
retriever = retriever_obj.load_retriever()

duckduckgo = DuckDuckGoSearchRun()

def format_docs(docs) -> str:
    """Format retriever docs into readable context."""
    if not docs:
        return ""
    chunks = []
    for d in docs:
        meta = d.metadata or {}
        formatted = (
            f"Title: {meta.get('product_title', 'N/A')}\n"
            f"Price: {meta.get('price', 'N/A')}\n"
            f"Rating: {meta.get('rating', 'N/A')}\n"
            f"Review:\n{(d.page_content or '').strip()}"
        )
        chunks.append(formatted)
    return "\n\n---\n\n".join(chunks)

@mcp.tool()
async def get_product_info(query: str) -> str:
    """
    Retrieve product information for a given query from the local retriever.
    """
    try:
        docs = retriever.invoke(query)
        context = format_docs(docs)
        if not context.strip():
            return "No local results found."
        return context
    except Exception as e:
        return f"Error retrieving product info: {e}"

@mcp.tool()
async def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo when local retrieval is insufficient.
    """
    try:
        # DuckDuckGoSearchRun supports invoke(query) in LC 0.3.x
        return duckduckgo.invoke(query)
    except Exception as e:
        return f"Error during web search: {e}"

if __name__ == "__main__":
    # Pick the transport you actually use. stdio is common for local dev.
    mcp.run(transport="stdio")
