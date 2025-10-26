import os
from openai import OpenAI
from langchain.tools import StructuredTool
from dotenv import load_dotenv
from ...prompts.c1_assistent_prompt import ASSISTANT_UI_SPEC
from pydantic import BaseModel, Field

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
