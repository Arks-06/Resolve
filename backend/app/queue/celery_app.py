"""
Instantiates the distributed Celery task architecture, pointing to Redis as both the message broker and result backend.
Patches the Windows-specific asyncio event loop policies to prevent background worker socket crashes.
"""

import sys
import asyncio
from dotenv import load_dotenv
from celery import Celery
from app.core.config import settings

# Enforce standard selector policy on Windows to prevent Proactor teardown socket crashes
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Explicitly load the .env file into the worker's OS environment
load_dotenv()


# Initialize distributed task queue with Redis acting as both message broker and result backend
celery_app = Celery(
    "resolve_queue",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.queue.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)