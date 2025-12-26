from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

from app.core.config import APP_VERSION
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspace_router
from app.core.database import test_db_connection
from app.api.v1.documents import router as documents_router
from app.api.v1.chunks import router as chunks_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.answer import router as answer_router

app = FastAPI(title="GroundedAI Backend", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "groundedai-backend"}


@app.get("/db-health")
def db_health():
    try:
        test_db_connection()
        return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}


app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(documents_router)
app.include_router(chunks_router)
app.include_router(embeddings_router)
app.include_router(retrieval_router)
app.include_router(answer_router)