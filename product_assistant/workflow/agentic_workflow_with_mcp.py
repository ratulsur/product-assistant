from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from product_assistant.retriever.retrieval import Retriever
from product_assistant.utils.model_loader import ModelLoader
from langgraph.checkpoint.memory import MemorySaver
import asyncio
#from evaluation.ragas_eval import evaluate_context_precision, evaluate_response_relevancy
from langchain_mcp_adapters.client import MultiServerMCPClient

class AgenticRAG:
    """
    Agentic RAG pipeline to address customer query
    """

    class AgenticState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

        def __init__(self):
            self.retriever_obj = Retriever()
            self.model_loader = ModelLoader()
            self.llm = self.model_loader.load_llm()
            self.checkpinter = MemorySaver()

            self.mcp_client = MultiServerMCPClient({
                "product_retriever": {
                    "command": "python",
                    "args": ["/Users/ratulsur/Desktop/all_data/prod_asst/product_assistant/mcp_servers/product_search_server.py"],
                    "transport": "stdio"
                }
            })

            self.mcp_tools = asyncio.run(self.mcp_client.get_tools())

            self.workflow = self._build_workflow()
            self.app = self.workflow.compile(checkpointer = self.checkpointer)
        def _format_docs(self, docs)->str:
            if not docs:
                return "no relevant docs found"
            formatted_chunks = []
            for d in docs:
                meta = d.metadata or {}
                formatted = (
                f"Title: {meta.get("product_title", "N/A")}\n"
                f"Price: {meta.get("price", "N?A")}\n"
                f"Rating: {meta.get("rating", "N/A")}\n"
                f"Reviews: \n{d.page_content.strip()}"

                )
                formatted_chunks.append(formatted)
                return "\n\n---\n\n".join(formatted_chunks)
        #-----------NODES---------

        


