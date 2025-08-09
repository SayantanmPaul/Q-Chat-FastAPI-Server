from fastapi import HTTPException
from typing import Optional

MODEL_LIST= [
    {
        "name": "gemini-2.5-flash-lite",
        "description": "Google's most cost-efficient model"
    },
    {
        "name": "openai/gpt-oss-20b",
        "description": "OpenAI's compact open-weight model"
    },
    {
        "name": "openai/gpt-oss-120b",
        "description": "OpenAI's flagship open-weight model"
    },
]


def select_model(raw: Optional[str]) -> str:
    if not raw:
        return MODEL_LIST[0]["name"]
    
    raw = str(raw).strip()

    if raw.isdigit():
        idx = int(raw)
        if 0 <= idx < len(MODEL_LIST):
            return MODEL_LIST[idx]["name"]
        raise HTTPException(status_code=400, detail=f"Invalid model index {idx}")

    # if user passed a name
    names = {m["name"] for m in MODEL_LIST}
    if raw in names:
        return raw

    raise HTTPException(
        status_code=400,
        detail=f"Unknown model '{raw}'. Allowed: {', '.join(names)}",
    )