from typing import AsyncGenerator, Optional
from fastapi import HTTPException
from ..services.langgraph_agent import generate_chat_responses

class AgentService:
    async def stream_chat(
        self,
        message: str,
        checkpoint_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in generate_chat_responses(message, model_name, checkpoint_id):
            yield chunk