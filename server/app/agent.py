"""pydantic-ai Agent setup for the LibSync chat assistant.

Mirrors the original Hugging Face Inference API setup: same provider (novita),
same model (deepseek-ai/DeepSeek-V3.2-Exp), same system prompt structure, so
the assistant's behavior is unchanged from the Node.js implementation.
"""

from pydantic_ai import Agent
from pydantic_ai.models.huggingface import HuggingFaceModel
from pydantic_ai.providers.huggingface import HuggingFaceProvider

from app.bot_context.bill_of_rights import ALA_BILL_OF_RIGHTS
from app.bot_context.core_values import ALA_CORE_VALUES
from app.bot_context.identity import PERSONA_PROMPT
from app.bot_context.rusa_guidelines import RUSA_GUIDELINES
from app.config import HUGGINGFACE_TOKEN

# The system prompt provides the AI with its core identity, instructions, and
# knowledge base. It is structured using XML-style tags to create a clear
# hierarchy for the model to follow, and is sent with every user message.
SYSTEM_PROMPT = f"""
<primary_instructions>
{PERSONA_PROMPT}
</primary_instructions>

<guiding_principles>
<knowledge_source name="RUSA Guidelines for Behavioral Performance">
{RUSA_GUIDELINES}
</knowledge_source>

<knowledge_source name="ALA Library Bill of Rights">
{ALA_BILL_OF_RIGHTS}
</knowledge_source>

<knowledge_source name="ALA Core Values of Librarianship">
{ALA_CORE_VALUES}
</knowledge_source>

</guiding_principles>
"""

_model = HuggingFaceModel(
    "deepseek-ai/DeepSeek-V3.2-Exp",
    provider=HuggingFaceProvider(api_key=HUGGINGFACE_TOKEN, provider_name="novita"),
)

chat_agent = Agent(_model, system_prompt=SYSTEM_PROMPT)


async def get_chat_reply(message: str) -> str:
    """Send a user's message to the chat agent and return its text reply.

    Raises:
        RuntimeError: If the underlying model call fails.
    """
    try:
        print("Received message:", message)
        result = await chat_agent.run(message)
        print("Agent reply:", result.output)
        return result.output
    except Exception as error:
        print("Agent error:", error)
        raise RuntimeError(
            "⚠️ Error: Unable to reach AI service. Please try again later."
        ) from error
