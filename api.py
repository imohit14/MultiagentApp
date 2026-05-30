from fastapi import FastAPI
from pydantic import BaseModel

from main import run_multi_agent

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def health():
    return {
        "status": "running"
    }


@app.post("/chat")
async def chat(req: ChatRequest):

    response = await run_multi_agent(req.message)

    return {
        "response": response
    }