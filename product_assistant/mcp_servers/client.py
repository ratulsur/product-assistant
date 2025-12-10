import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "mcp_servers", "product_search_server.py")
)


async def main():
    client = MultiServerMCPClient({
        "hybrid_search": {
            "command": "python",
            "args": [SERVER_PATH],
            "transport": "stdio"
        }
    })

    # Load tools from MCP server
    tools = await client.get_tools()

    # Ensure tool names match your MCP tool definitions
    retriever_tool = next(t for t in tools if t.name == "get_product_info")
    web_tool = next(t for t in tools if t.name == "web_search")

    query = "price of iPhone 15"

    # Call retriever
    retriever_result = await retriever_tool.ainvoke({"query": query})
    print("\nRetriever Result:\n", retriever_result)

    # Fallback to web search if no local results
    if not retriever_result or "no" in retriever_result.lower():
        print("\nNo local results, falling back to web search...\n")
        web_result = await web_tool.ainvoke({"query": query})
        print("\nWeb Search Result:\n", web_result)


if __name__ == "__main__":
    asyncio.run(main())
