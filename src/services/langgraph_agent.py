from typing import TypedDict, Optional, Annotated
from langgraph.graph import add_messages, StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.agents import tool
from langchain_core.messages import AIMessageChunk, HumanMessage, ToolMessage, SystemMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_community.tools import GoogleSerperResults
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.memory import MemorySaver
from ..sys_prompt import CUSTOM_SYSTEM_PROMPT
from uuid import uuid4
import json

load_dotenv()

MODEL_NAME= "gemini-2.0-flash-lite"


# Initialize memory saver for checkpointing
memory = MemorySaver()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# tavely search tool initialization, max_result set to 4
search_tools= TavilySearchResults()


# tools 
tools= [search_tools]

model= ChatGoogleGenerativeAI(model= MODEL_NAME)

llm_with_tools= model.bind_tools(tools= tools)

# injecting system prompt to the graph
async def start_node(state: AgentState):
    sys_message= SystemMessage(content= CUSTOM_SYSTEM_PROMPT)
    return {"messages": [sys_message]}


# this node is going to get enire state and will use llm_with_tools to invoke and pass the list of messages and update the state with the result
async def model(state: AgentState):
    # while using async/await use ainvoke method instead of invoke 
    result = await llm_with_tools.ainvoke(state["messages"])
    return { 
        "messages": [result],
    }

async def tools_router(state: AgentState):
    last_message = state["messages"][-1]

    if(hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0):
        return "tool_node"
    else: 
        return END

async def tool_node(state):
    """Custom tool node that handle all the tool calls from the LLM itself"""
    # get the tool calls from the last message
    tool_calls= state["messages"][-1].tool_calls

    # initialize the list of tool messages
    tool_messages= []

    # process each tool call
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"] # internet search quwey 
        tool_id = tool_call["id"]

        # handle the tool call using the tool
        if tool_name == "tavily_search_results_json":
            # execute the tool call with the args
            search_results = await search_tools.ainvoke(tool_args)

            # create a tool message with the results
            tool_message = ToolMessage(
                content=str(search_results),
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(tool_message)

    # Add the tool messages to the state
    return {"messages": tool_messages}

# build the state graph
graph_builder = StateGraph(AgentState)

graph_builder.add_node("inject_system_prompt", start_node)
graph_builder.add_node("model", model)
graph_builder.add_node("tool_node", tool_node)

graph_builder.set_entry_point("inject_system_prompt")
graph_builder.add_edge("inject_system_prompt", "model")
graph_builder.add_conditional_edges("model", tools_router)
graph_builder.add_edge("tool_node", "model")

graph = graph_builder.compile(checkpointer= memory)


# serialize llm message chunk
def serialise_ai_message_chunk(chunk): 
    if(isinstance(chunk, AIMessageChunk)):
        return chunk.content
    else:
        raise TypeError(
            f"Object of type {type(chunk).__name__} is not correctly formatted for serialisation"
        )


async def generate_chat_responses(message: str, checkpoint_id: Optional[str] = None):
    is_new_conversation = checkpoint_id is None
    
    if is_new_conversation:
        # Generate new checkpoint ID for first message in conversation
        new_checkpoint_id = str(uuid4())

        config = {
            "configurable": {
                "thread_id": new_checkpoint_id
            }
        }
        
        # Initialize with first message
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config
        )
        
        # First send the checkpoint ID
        yield f"data: {{\"type\": \"checkpoint\", \"checkpoint_id\": \"{new_checkpoint_id}\"}}\n\n"
    else:
        config = {
            "configurable": {
                "thread_id": checkpoint_id
            }
        }
        # Continue existing conversation
        events = graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            version="v2",
            config=config
        )

    async for event in events:
        event_type = event["event"]
        
        if event_type == "on_chat_model_stream":
            chunk_content = event["data"]["chunk"].content

            # let json.dumps handle all the escaping
            payload = {
                "type": "content",
                "content": chunk_content
            }
            yield f"data: {json.dumps(payload)}\n\n"
            
        elif event_type == "on_chat_model_end":
            # Check if there are tool calls for search
            tool_calls = event["data"]["output"].tool_calls if hasattr(event["data"]["output"], "tool_calls") else []
            search_calls = [call for call in tool_calls if call["name"] == "tavily_search_results_json"]
            
            if search_calls:
                payload = {
                    "type": "search_start",
                    "query": search_calls[0]["args"].get("query", "")
                }
                yield f"data: {json.dumps(payload)}\n\n"

        elif event_type == "on_tool_end" and event["name"] == "tavily_search_results_json":
            # Search completed - send results or error
            output = event["data"]["output"]
            
            # Check if output is a list 
            if isinstance(output, list):
                # Extract URLs from list of search results
                urls = []
                for item in output:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
                
                payload = {
                    "type": "search_results",
                    "urls": urls
                }
                yield f"data: {json.dumps(payload)}\n\n"
    
    # Send an end event
    yield f"data: {{\"type\": \"end\"}}\n\n"    