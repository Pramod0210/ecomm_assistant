from enum import Enum
from typing import Dict
import string


class PromptType(str, Enum):
    PRODUCT_BOT = "product_bot"
    # REVIEW_BOT = "review_bot"
    # COMPARISON_BOT = "comparison_bot"


class PromptTemplate:
    def __init__(self, template: str, description: str = "", version: str = "v1"):
        """
        Initialize PromptTemplate object.

        Args:
            template (str): Template string containing placeholders.
            description (str, optional): Description of the template. Defaults to "".
            version (str, optional): Version of the template. Defaults to "v1".
        """
        self.template = template.strip()
        self.description = description
        self.version = version

    def format(self, **kwargs) -> str:
        # Validate placeholders before formatting
        """
        Format the template string with given keyword arguments.

        Args:
            **kwargs: Keyword arguments containing values to replace placeholders.

        Returns:
            str: Formatted template string.

        Raises:
            ValueError: If any required placeholders are missing from kwargs.
        """
        missing = [
            f for f in self.required_placeholders() if f not in kwargs
        ]
        if missing:
            raise ValueError(f"Missing placeholders: {missing}")
        return self.template.format(**kwargs)

    def required_placeholders(self):
        """
        Returns a list of required placeholder names from the template string.
        These are the placeholder names that must be provided as keyword arguments
        when calling the format method.

        Returns:
            List[str]: List of required placeholder names.
        """
        return [field_name for _, field_name, _, _ in string.Formatter().parse(self.template) if field_name]


# Central Registry
PROMPT_REGISTRY: Dict[PromptType, PromptTemplate] = {
    PromptType.PRODUCT_BOT: PromptTemplate(
        """
        You are an expert EcommerceBot specialized in product recommendations and handling customer queries.
        Analyze the provided product titles, ratings, and reviews to provide accurate, helpful responses.
        Stay relevant to the context, and keep your answers concise and informative.

        CONTEXT:
        {context}

        QUESTION: {question}

        YOUR ANSWER:
        """,
        description="Handles ecommerce QnA & product recommendation flows"
    )
}