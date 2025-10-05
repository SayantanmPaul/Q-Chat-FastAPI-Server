from typing import TypedDict, Annotated
from langgraph.graph import add_messages, StateGraph, END
# from langchain.agents import tool
from langchain_core.messages import  ToolMessage, SystemMessage
from dotenv import load_dotenv
from langchain_community.tools import GoogleSerperResults
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langgraph.checkpoint.memory import MemorySaver
from ...prompts.sys_prompt import CUSTOM_SYSTEM_PROMPT
from .tools import CreateC1GenUITool

from uuid import uuid4
import json

load_dotenv()

# Initialize memory saver for checkpointing
memory = MemorySaver()

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# tavely search tool initialization, max_result set to 4
search_tools= TavilySearchResults()
yahoo_finance_news_tool= YahooFinanceNewsTool()
c1_tool= CreateC1GenUITool()

# tools 
tools= [search_tools, yahoo_finance_news_tool , c1_tool]

def build_graph(ai_model):
    llm_with_tools= ai_model.bind_tools(tools= tools)

    # injecting system prompt to the graph
    async def start_node(state: AgentState):
        sys_message= SystemMessage(content= CUSTOM_SYSTEM_PROMPT)
        return {"messages": [sys_message]}

    # this node is going to get enire state and will use llm_with_tools to invoke and pass the list of messages and update the state with the result
    async def model_node(state: AgentState):
    # while using async/await use ainvoke method instead of invoke 
        result = await llm_with_tools.ainvoke(state["messages"])
        return { 
            "messages": [result],
        }

    async def tools_router(state: AgentState):
        last_message = state["messages"][-1]

        calls= getattr(last_message, "tool_calls", []) or []
        return "tool_node" if calls else END

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

            # Handle different tools
            if tool_name == "tavily_search_results_json":
                # execute the tool call with the args
                search_results = await search_tools.ainvoke(tool_args)

                # create a tool message with the results
                tool_message = ToolMessage(
                    content=json.dumps(search_results, ensure_ascii=False),
                    tool_call_id=tool_id,
                    name=tool_name
                )

            # Handle Yahoo Finance News
            elif tool_name == "yahoo_finance_news": 
                try:
                    finance_results = await yahoo_finance_news_tool.ainvoke(tool_args)
                except Exception as e:
                    finance_results = {"error": f"yahoo_finance_news failed: {type(e).__name__}: {e}"}
                tool_message = ToolMessage(
                    content=json.dumps(finance_results, ensure_ascii=False),
                    tool_call_id=tool_id,
                    name=tool_name
                )
            
            # Handle Thesys C1 Generative UI
            elif tool_name == "c1_ui_generate": 
                c1_results = await c1_tool.ainvoke(tool_args)
                tool_message = ToolMessage(
                    content=c1_results,
                    tool_call_id=tool_id,
                    name=tool_name,
                )
            
            else:
                tool_message = ToolMessage(
                    content=f"Unknown tool: {tool_name}",
                    tool_call_id=tool_id,
                    name=tool_name
                )

            tool_messages.append(tool_message)

        # Add the tool messages to the state
        return {"messages": tool_messages}

    # build the state graph
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("inject_system_prompt", start_node)
    graph_builder.add_node("model", model_node)
    graph_builder.add_node("tool_node", tool_node)

    graph_builder.set_entry_point("inject_system_prompt")
    graph_builder.add_edge("inject_system_prompt", "model")
    graph_builder.add_conditional_edges("model", tools_router)
    graph_builder.add_edge("tool_node", "model")

    return graph_builder.compile(checkpointer= memory)

