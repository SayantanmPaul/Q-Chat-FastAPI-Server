import os
from openai import OpenAI
from langchain.tools import StructuredTool
from dotenv import load_dotenv
from ...prompts.c1_assistent_prompt import ASSISTANT_UI_SPEC
from pydantic import BaseModel, Field
from typing import Iterable, Optional, List
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.documents import Document
from langchain_core.tools import BaseTool
from requests.exceptions import HTTPError, ReadTimeout
from urllib3.exceptions import ConnectionError
from langchain_community.document_loaders.web_base import WebBaseLoader
load_dotenv()

THESYS_API_KEY= os.getenv("THESYS_API_KEY")

client = OpenAI(
    api_key = THESYS_API_KEY,
    base_url="https://api.thesys.dev/v1/embed"
)

class C1Args(BaseModel):
    context: str = Field(..., description="System/UI context to guide generation.")
    user_query: str = Field(..., description="User request or prompt to transform into UI copy.")

# Thesys C1 API as Tool
def CreateC1GenUITool():
    def call_c1_for_ui(context: str, user_query: str) -> str:
        # Call C1 API with context and query
        resp = client.chat.completions.create(
            model="c1/openai/gpt-5/v-20250915",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_query},
                { "role": "assistant", "content": ASSISTANT_UI_SPEC },
            ],
            temperature=0.2,
            stream= False,
        )
        return resp.choices[0].message.content

    return StructuredTool.from_function(
        name="c1_ui_generate",
        description=(
            "Generate/transform UI copy using C1. "
            "Always call with: {\"context\": \"...\", \"user_query\": \"...\"}."
        ),
        func=call_c1_for_ui,
        args_schema=C1Args
    )


# Not used ~ Ignore !!!!
class YahooFinanceNewsTool(BaseTool):
    """Tool that searches financial news on Yahoo Finance."""

    name: str = "yahoo_finance_news"
    description: str = (
        "Useful for when you need to find financial news "
        "about a public company. "
        "Input should be a company ticker. "
        "For example, AAPL for Apple, MSFT for Microsoft."
    )
    top_k: int = 10
    """The number of results to return."""

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the Yahoo Finance News tool."""
        try:
            import yfinance
        except ImportError:
            raise ImportError(
                "Could not import yfinance python package. "
                "Please install it with `pip install yfinance`."
            )
        
        ticker = (query or "").strip().upper()
        if not ticker:
            return "Please provide a non-empty company ticker symbol."
        
        company = yfinance.Ticker(query)

        try:
            _ = company.isin  # may raise on bad ticker/network
        except Exception:
            pass

        items: List[dict] = []
        try:
            items = company.news or []
        except (HTTPError, ReadTimeout, ConnectionError) as e:
            return f"Failed to fetch Yahoo Finance news for {ticker}: {type(e).__name__}: {e}"
        except Exception as e:
            return f"Unexpected error fetching news for {ticker}: {type(e).__name__}: {e}"

        # Extract links safely; do NOT assume "type" exists
        links = []
        titles = []
        descriptions = []
        for n in items:
            link = n.get("link")
            if not link:
                continue
            links.append(link)
            titles.append(n.get("title", ""))
            descriptions.append(n.get("content", "") or n.get("publisher", "") or "")

            if len(links) >= self.top_k:
                break

        if not links:
            return f"No news found for ticker {ticker}."

        # Try to load the articles; if scraping fails entirely, fall back to title+link list
        docs: List[Document] = []
        try:
            loader = WebBaseLoader(web_paths=links)
            docs = loader.load()
        except Exception:
            # proceed with fallback formatting using raw Yahoo items
            pass

        if docs:
            result = self._format_results(docs, ticker)
            if result:
                return result

        # Fallback: format from Yahoo metadata if scraping didn’t yield descriptions
        lines = []
        for i, link in enumerate(links):
            t = titles[i] if i < len(titles) else ""
            d = descriptions[i] if i < len(descriptions) else ""
            lines.append(f"{t}\n{d}\n{link}")
        return "\n\n".join(lines) if lines else f"No news found for ticker {ticker}."

    async def _arun(
            self,
            query: str,
            run_manager: Optional["CallbackManagerForToolRun"] = None,
    ) -> str:
        # Simple async wrapper; yfinance + loader are sync, so run in thread executor if desired.
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, query)

    @staticmethod
    def _format_results(docs: Iterable[Document], query: str) -> str:
        doc_strings = [
            "\n".join([doc.metadata["title"], doc.metadata["description"]])
            for doc in docs
            if "description" in doc.metadata
            and (query in doc.metadata["description"] or query in doc.metadata["title"])
        ]
        return "\n\n".join(doc_strings)