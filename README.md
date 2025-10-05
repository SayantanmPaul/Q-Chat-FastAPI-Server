# Q-Chat FastAPI Server

Backend server for Q-Chat, an agentic financial advisory assistant.

Built with FastAPI, it uses LangChain and LangGraph to provide contextual financial guidance, with a focus on the Indian market.
## Base Overview

- **High-Performance API**: Built on FastAPI for asynchronous, high-speed request handling.

- **Advanced Agentic Architecture**: Uses LangGraph to create a robust, multi-step agent that can reason and use tools.

- **Multi-Model Support**: Integrates with a set of llm via OpenRouter `cerebras.ai`

- **Dynamic Tool Use**: The agent has a selection of tools:
    - **Web Search**: `TavilySearchResults` for up-to-date information.

    - **Financial News**: `YahooFinanceNewsTool` for market and company news.

    - **Generative UI**: `c1_tool` to generate JSON specifications for UI components, enabling , visual responses `generative ui` on the client side.

- **Streaming Responses**: Utilizes Server-Sent Events (SSE) to stream responses token-by-token, providing a real-time chat experience.
- **Conversation History**: Manages conversational state with checkpointing, allowing for multi-turn dialogues.
- **Containerized**: Includes `Dockerfile` and `docker-compose.yml` for easy and consistent deployment.
- **Rate Limiting**: Basic protection against abuse with a per-IP rate limit.

## System Architecture

The server's workflow is orchestrated by a LangGraph state machine:

-   **Request Handling**: A user query is sent to the `/api/v2/chat-stream` endpoint.
-  **Graph Initialization**: A new / existing conversational graph is configured. A system prompt (`CUSTOM_SYSTEM_PROMPT`) is injected, instructing the agent to act based on it. 
-  **Model Invocation**: The agent's core LLM make decision the next step: respond directly or use a tool.
- **Tool Routing**: If a tool is chosen, the graph routes the state to the `tool_node`.
- **Tool Execution**: The selection tool (`Tavily`, `YahooFinanceNews`, or `c1_ui_generate`) is executed. 
- **Response Generation**: The output from the tool is passed back to the model, which finised weather it the final response.
- **Streaming**: Throughout this process, events (`content`, `tool_starts`, `tool_outputs`, `end`) are streamed back to the client as SSE.

## Getting Started

### Prerequisites

-   Python 3.11
-   Docker and Docker Compose (Recommended)

### Environment Variables

Create a `.env` file in the root of the project and add your API keys. The `docker-compose.yml` is configured to load this file.

```.env
# Get from https://openrouter.ai/
OPENROUTER_API_KEY="..."

# Get from https://www.thesys.dev/
THESYS_API_KEY="..."

# Get from https://aistudio.google.com/
GOOGLE_API_KEY= "..."

# Get from https://tavily.com/
TAVILY_API_KEY="tvly-..."

# Client URL for CORS
CLIENT_URL="http://localhost:3000"
```

### Project Setup and Usage

#### Using Docker (Recommended)

This is the easiest way to get the server running.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sayantanmpaul/Q-Chat-FastAPI-Server.git
    cd Q-Chat-FastAPI-Server
    ```

2.  **Create your `.env` file** as described above.

3.  **Build and run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

The server will be available at `http://localhost:8000`.

#### Local Development

1.  **Clone the repository and navigate into it.**

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate 
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create your `.env` file.**

5.  **Run the application with Uvicorn:**
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ```
