from starlette.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from .services.router import router as agents_router
from .rate_limiting import limiter

from fastapi import FastAPI
import uvicorn


app=FastAPI()

# Attach rate limiter middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# add CROS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-type"],
)

# Mount agents router
app.include_router(agents_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)