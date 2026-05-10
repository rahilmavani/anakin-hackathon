from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent import run_agent_stream
from .models import AnalyzeRequest


app = FastAPI(title="TenderFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> StreamingResponse:
    stream = run_agent_stream(req.query)
    return StreamingResponse(stream, media_type="text/event-stream")
