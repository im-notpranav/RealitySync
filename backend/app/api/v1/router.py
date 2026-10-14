from fastapi import APIRouter

from app.api.v1 import api_keys, auth, ingest, users

api_router = APIRouter()
# Add include_router lines here as modules are built
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)
api_router.include_router(ingest.router)
