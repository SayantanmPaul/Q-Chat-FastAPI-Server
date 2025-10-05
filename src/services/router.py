import os
import psutil
from pydantic import BaseModel
from typing import Optional
from .service_agent import AgentService
from ..rate_limiting import limiter
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from .builder.model_selection import MODEL_LIST
from .builder.model_selection import select_model

class AgentRequest(BaseModel):
    message: str
    checkpoint_id: Optional[str] = None

router = APIRouter(
    prefix="/api/v2",
    tags=["agents"],
)

# Chat
@router.get( "/chat-stream", response_class=StreamingResponse )

@limiter.limit("10/minute")
async def chat_stream(
    request: Request,
    message: str = Query(...),
    checkpoint_id: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    service: AgentService = Depends(),
):
    choosen= select_model(model_name)
    return StreamingResponse(
        service.stream_chat(message, checkpoint_id, choosen),
        media_type="text/event-stream",
    )

@router.get("/getModelName", status_code=status.HTTP_200_OK)
async def get_model_name():
    return {"data": MODEL_LIST}

@router.get("/health", status_code=status.HTTP_200_OK)

async def health_check():
    """ health check endpoint"""

    # Memory usage
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    memory_usage = {
        "heapTotal": mem_info.vms / (1024 ** 2),
        "heapUsed": mem_info.rss / (1024 ** 2)
    }

    # System info
    cpu_percents = psutil.cpu_percent(percpu=True)
    virtual_mem = psutil.virtual_memory()
    system_info = {
        "cpuUsage": cpu_percents,
        "totalMemory": virtual_mem.total / (1024 ** 2),
        "freeMemory": virtual_mem.available / (1024 ** 2)
    }

    health_data = {
        "memoryUsage": memory_usage,
        "system": system_info,
    }
    return JSONResponse(health_data)
