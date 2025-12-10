from enum import Enum
from typing import Dict
import string


class PromptType(str, Enum):
    PRODUCT_BOT = "product_bot"


class PromptTemplate:
    def __init__(self, template: str, description: str = "", version: str = "v1"):
        self.template = template.strip()
        self.description = description
        self.version = version

    def format(self, **kwargs) -> str:
        missing = [f for f in self.required_placeholders() if f not in kwargs]
        if missing:
            raise ValueError(f"Missing placeholders: {missing}")
        return self.template.format(**kwargs)

    def required_placeholders(self):
        return [
            field_name
            for _, field_name, _, _ in string.Formatter().parse(self.template)
            if field_name
        ]


PROMPT_REGISTRY: Dict[PromptType, PromptTemplate] = {
    PromptType.PRODUCT_BOT: PromptTemplate(
        """
        You are an expert Ecommerce bot specialized in product recommendations and answering
        customer queries.
        Analyze the provided product titles, prices, ratings, and reviews to provide accurate answers
        based on their queries.
        Stay relevant to the context and make the answer short, informative, and helpful.

        CONTEXT:
        {context}

        QUESTION:
        {question}

        YOUR ANSWER:
        """,
        description="handles customer Q&A",
    )
}
