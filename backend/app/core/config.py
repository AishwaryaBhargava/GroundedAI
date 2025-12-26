import os
from dotenv import load_dotenv

load_dotenv()

# App
APP_VERSION = os.getenv("APP_VERSION", "local-dev")

# Azure OpenAI (shared)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Embeddings
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"
)
AZURE_OPENAI_EMBEDDINGS_API_VERSION = os.getenv(
    "AZURE_OPENAI_EMBEDDINGS_API_VERSION"
)

# Chat / Answers
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_CHAT_DEPLOYMENT"
)
AZURE_OPENAI_CHAT_API_VERSION = os.getenv(
    "AZURE_OPENAI_CHAT_API_VERSION"
)

# Safety checks (fail fast)
if not AZURE_OPENAI_ENDPOINT:
    raise RuntimeError("AZURE_OPENAI_ENDPOINT not set")

if not AZURE_OPENAI_API_KEY:
    raise RuntimeError("AZURE_OPENAI_API_KEY not set")
