from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
# from langchain.agents import tool
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .builder.graph_builder import build_graph
from uuid import uuid4
import json
import os


load_dotenv()

OPENROUTER_API_KEY= os.getenv("OPENROUTER_API_KEY")

def make_model(model_name: str):
    """Return a ready-to-use LLM instance based on the model name."""

    if model_name== "gemini-2.5-flash-lite":
        return ChatGoogleGenerativeAI(model= model_name)    
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key= OPENROUTER_API_KEY,
        model_name= model_name
    )

# serialize llm message chunkz
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
    
    # generate checkpoint id
    thread_id= str(uuid4()) if is_new_conversation else checkpoint_id

    if is_new_conversation:
        # Send the checkpoint ID if new conversation
        yield f'data: {{"type": "checkpoint", "checkpoint_id": "{thread_id}"}}\n\n'
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        events = graph.astream_events(
                {"messages": [HumanMessage(content=message)]},
                version="v2",
                config= config
            )
        
        emitted_any_content = False

        async for event in events:
            event_type = event["event"]

            if event_type == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content

                if chunk:
                    emitted_any_content= True
                    payload = {
                        "type": "content",
                        "content": chunk
                    }
                    yield f'data: {json.dumps(payload)}\n\n'

            # Check if there are tool calls for search
            elif event_type == "on_chat_model_end":
                # emit final text if no stream chunks were seen
                output = event["data"]["output"]
                final_text = getattr(output, "content", None)

                if final_text and not emitted_any_content:
                    payload = {
                        "type": "content",
                        "content": final_text
                    }
                    yield f'data: {json.dumps(payload)}\n\n'

                # handle tool calls
                tool_calls = getattr(output, "tool_calls", []) or []
                search_calls = [call for call in tool_calls if call.get("name") == "tavily_search_results_json"]

                if search_calls:
                    payload = {
                        "type": "search_start",
                        "query": search_calls[0]["args"].get("query", "")
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            # handle search url list
            elif event_type== "on_tool_end" and event.get("name") == "tavily_search_results_json":
                out = event["data"]["output"]

                urls=[]
                if isinstance(out, list):
                    for i in out:
                        if isinstance(i, dict) and "url" in i:
                            urls.append(i["url"])

                payload = {
                        "type": "search_results",
                        "urls": urls
                    }
                yield f"data: {json.dumps(payload)}\n\n"
        
        # end of stream
        yield 'data: {"type":"end"}\n\n'

    # don’t raise after stream begins—send an error event instead
    except Exception as e:
        yield f'data: {json.dumps({"type":"error","message": str(e)})}\n\n'
        yield 'data: {"type":"end"}\n\n'