"""
lore-daemon HTTP server — listens on port 7340 for Claude Code hook events.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lore_daemon.hooks import compact, pre_tool, prompt, stop, tool

app = FastAPI(title="lore-daemon", version="0.1.0")


@app.post("/hooks/prompt")
async def hook_prompt(request: Request):
    payload = await request.json()
    context = prompt.handle(payload)
    return JSONResponse(context)


@app.post("/hooks/tool")
async def hook_tool(request: Request):
    payload = await request.json()
    tool.handle(payload)
    return JSONResponse({})


@app.post("/hooks/compact")
async def hook_compact(request: Request):
    payload = await request.json()
    compact.handle(payload)
    return JSONResponse({})


@app.post("/hooks/stop")
async def hook_stop(request: Request):
    payload = await request.json()
    stop.handle(payload)
    return JSONResponse({})


@app.post("/hooks/pre-tool")
async def hook_pre_tool(request: Request):
    payload = await request.json()
    context = pre_tool.handle(payload)
    return JSONResponse(context)


@app.get("/health")
async def health():
    return {"status": "ok"}
