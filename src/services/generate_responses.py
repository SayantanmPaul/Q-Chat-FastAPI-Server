from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
# from langchain.agents import tool
from langchain_core.messages import AIMessageChunk, HumanMessage
from dotenv import load_dotenv
from ..builder.graph_builder import build_graph
from uuid import uuid4
import json
import os


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is required for non-Gemini models")


def make_model(model_name: str):
    """Returns a ready-to-use LLM instance based on the model name."""

    if model_name== "gemini-2.5-flash-lite":
        return ChatGoogleGenerativeAI(model= model_name)    
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key= OPENROUTER_API_KEY,
        model_name= model_name
    )

# serialize llm message chunks
def serialise_ai_message_chunk(chunk): 
    if(isinstance(chunk, AIMessageChunk)):
        return chunk.content
    else:
        raise TypeError(
            f"Object of type {type(chunk).__name__} is not correctly formatted for serialisation"
        )

async def generate_chat_responses(
    message: str,
    model_name: str,
    checkpoint_id: Optional[str] = None
): 
    llm = make_model(model_name)
    graph = build_graph(llm)

    is_new_conversation = checkpoint_id is None
    thread_id = str(uuid4()) if is_new_conversation else checkpoint_id

    if is_new_conversation:
        yield f'data: {{"type": "checkpoint", "checkpoint_id": "{thread_id}"}}\n\n'
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config
        )
        
        emitted_any_content = False
        event_id = 1

        async for event in events:
            event_type = event["event"]

            # Stream tokens from the chat model
            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content

                if chunk:
                    emitted_any_content = True
                    # Proper SSE format with id
                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "content", "content": chunk})}\n\n'
                    event_id += 1

            elif event_type == "on_chat_model_end":
                output = event["data"]["output"]
                final_text = getattr(output, "content", None)

                if final_text and not emitted_any_content:
                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "content", "content": final_text})}\n\n'
                    event_id += 1

                # Handle tool calls
                tool_calls = getattr(output, "tool_calls", []) or []

                # Existing search start (unchanged)
                search_calls = [call for call in tool_calls if call.get("name") == "tavily_search_results_json"]
                if search_calls:
                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "search_start", "query": search_calls[0]["args"].get("query", "")})}\n\n'
                    event_id += 1
                
                # announce upcoming C1 UI generation
                ui_calls = [c for c in tool_calls if c.get("name") == "c1_ui_generate"]
                if ui_calls:
                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "ui_start", "tool": "c1_ui_generate"})}\n\n'
                    event_id += 1

            elif event_type == "on_tool_end":
                tool_name = event.get("name")
                if tool_name == "tavily_search_results_json":
                    out = event["data"]["output"]
                    urls = []
                    if isinstance(out, list):
                        for i in out:
                            if isinstance(i, dict) and "url" in i:
                                urls.append(i["url"])

                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "search_results", "urls": urls})}\n\n'
                    event_id += 1
                
                elif tool_name == "c1_ui_generate":
                    tool_out = event["data"]["output"]
                    if isinstance(tool_out, str):
                        ui_content = tool_out
                    elif isinstance(tool_out, dict) and "content" in tool_out:
                        ui_content = tool_out["content"]
                    else:
                        # Fallback: best-effort JSON serialization
                        ui_content = json.dumps(tool_out, ensure_ascii=False)

                    yield f'id: {event_id}\n'
                    yield f'data: {json.dumps({"type": "ui_content", "tool": "c1_ui_generate", "content": ui_content})}\n\n'
                    event_id += 1
        
        # End of stream
        yield f'id: {event_id}\n'
        yield f'data: {json.dumps({"type": "end"})}\n\n'

    except Exception as e:
        try:
            event_id
        except NameError:
            event_id = 1
        yield f'id: {event_id}\n'
        yield f'data: {json.dumps({"type": "error", "message": str(e)})}\n\n'
        yield f'data: {json.dumps({"type": "end"})}\n\n'