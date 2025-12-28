from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from retriever.retrieval import Retriever
from utils.model_loader import ModelLoader
from langgraph.checkpoint.memory import MemorySaver
import asyncio
from evaluation.ragas_eval import evaluate_context_precision, evaluate_response_relevancy

class AgenticRAG:
    """
    AgenticRAG pipeline using LangGraph
    """

class AgenticState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

def __init__(self):
        self.retriever_obj = Retriever()
        self.model_loader = ModelLoader()
        self.llm_loader = self.model_loader.load_llm()
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer = self.checkpointer)

def _format_docs(self, docs) -> str:
        if not docs:
            return "no relevant docs found"
        formatted_chunks = []
        for d in docs:
            meta = d.metadata or {}
            formatted = (
                f"Title: {meta.get('product_title', 'N?A')}\n"
                f"Price: {meta.get("price", "N/A")}\n"
                f"Rating: {meta.get("rating", "N/A")}\n"
                f"Reviews: \n{d.page_content.strip()}"
            )
            formatted_chunks.append(formatted)

        return "\n\n---\n\n".join(formatted_chunks)
    
def _ai_assistant(self, state: AgenticState):
      print("---CALL ASSISTANT---")
      messages = state["messages"]
      last_message = messages[-1].content

      if any (word in last_message.lower() for word in ["price", "review","product" ]):
            return {"messages" : [HumanMessage(content="TOOL: retriever")]}
      else:
            prompt = ChatPromptTemplate.from_template(
                  "you are a helpful assistant. Answer the user directly.\n\nQuestion: {question}\nAnswer"
            )
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({"question":last_message})
            return {"messages": [HumanMessage(content=response)]}

def _vector_retriever(self, state: AgenticState):
      print("--RETRIEVER--")
      query = state["messages"][-1].content
      retriever = self.retriever_obj.load_retriever()
      docs = retriever.invoke(query)
      context = self._format_docs(docs)
      return {"messages": [HumanMessage(content=context)]}

def _grade_documents(self, state:AgenticState) -> Literal["generator", "rewriter"]:
      print("--GRADER--")
      question = state["messages"][0].content
      docs = state["messages"][-1].content

      prompt = PromptTemplate(
            template="""you are a grader. Question: {question}\nDocs :{docs}\n
            Are the docs relevant to the question. please answer in "yes" or "no"
""",
            input_variables=["question", "docs"],
      )
      chain = prompt | self.llm | StrOutputParser()
      score = chain.invoke({"question": question, "docs": docs})
      return "generator" if "yes" in score.lower() else "rewriter"

def _generate(self, state: AgenticState):
      print("--GENERATE--")
      question = state["messages"][0].content
      docs = state["messages"][-1].content

      prompt = ChatPromptTemplate.from_template(
            PROMPT_REGISTRY[PromptType.PRODUCT_BOT].template
            )
      chain = prompt | self.llm | StrOutputParser()
      response = chain.invoke({"context": docs, "question": question})
      return {"messages": [HumanMessage(content=response)]}

def _rewrite(self, state: AgenticState):
      print("--REWRITE--")
      question = state["messages"][0].content
      new_q = self.llm.invoke(
            [HumanMessage(content=f"Rewrite the query in a clearer way: {question}")]

      )
      return {"messages": [HumanMessage(content=new_q.content)]}

def _build_workflow(self):
      workflow = StateGraph(self.AgentState)
      workflow.add_node("Assistant", self._ai_assistant)
      workflow.add_node("Retriever", self._vector_assistant)
      workflow.add_node("Generator", self._generate)
      workflow.add_node("Rewriter", self._rewrite)

      workflow.add_edge(START, "Assistant")
      workflow.add_conditional_edges(
            
      )
      
