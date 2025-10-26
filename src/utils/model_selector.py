from fastapi import HTTPException
from typing import Optional

MODEL_LIST= [
    {
        "name": "openai/gpt-oss-120b",
        "description": "OpenAI's flagship open-weight model"
    },
    {
        "name": "qwen/qwen3-235b-a22b-2507",
        "description": "Qwen's multilingual language model"
    },
    {
        "name": "meta-llama/llama-4-scout",
        "description": "Meta's MoE language model"
    },
    {
        "name": "meta-llama/llama-3.3-70b-instruct",
        "description": "Meta's pretrained language model"
    },
    {
        "name": "gemini-2.5-flash-lite",
        "description": "Google's most cost-efficient model"
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