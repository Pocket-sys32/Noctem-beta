"""Noctem Virtual Dispatcher — FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.routers import carriers, loads, market, voice, transcripts, pins  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Noctem Virtual Dispatcher",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://noctem-beta.vercel.app",
    ],
    allow_origin_regex=r"^https://.*\\.vercel\\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(carriers.router)
app.include_router(loads.router)
app.include_router(market.router)
app.include_router(voice.router)
app.include_router(transcripts.router)
app.include_router(pins.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "noctem-backend"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "noctem-backend"}
