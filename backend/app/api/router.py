# Main API router — consolidates all routes to avoid conflicts
from fastapi import APIRouter

api_router = APIRouter()

# These are imported lazily in main.py to avoid circular imports
