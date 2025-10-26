from starlette.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from .router.v2.agent_routes import router as agents_router
from .router.limiter import limiter
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
import os

load_dotenv()

CLIENT_URL= os.getenv("CLIENT_URL")


# -----------------------------------------------------
# FastAPI Init
# -----------------------------------------------------

app=FastAPI( 
    title="Q-Chat Agent API", 
    description="Backend service for managing agent routes and rate limiting", 
    version="2.0.0"
)

# -----------------------------------------------------
# Middleware Configuration
# -----------------------------------------------------

# rate limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# add CROS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", CLIENT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-type"],
)

# base route
@app.get("/", tags=["Base"])
async def root():
    return {
        "message": "🚀 Welcome to Q-chat Agent API v2 — the backend is active and running!",
        "health_report": "/api/v2/health",
        "version": "2.0.0"
    }


# -----------------------------------------------------
# Routers
# -----------------------------------------------------
app.include_router(agents_router)

# Entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)