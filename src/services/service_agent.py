from typing import AsyncGenerator, Optional
from fastapi import HTTPException
from ..services.langgraph_agent import generate_chat_responses

class AgentService:
    async def stream_chat(self, message: str, checkpoint_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        try:
            async for chunk in generate_chat_responses(message, checkpoint_id):
                yield chunk
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))