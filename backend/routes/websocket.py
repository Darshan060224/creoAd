"""
WebSocket endpoint for real-time pipeline progress
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import asyncio
import redis.asyncio as aioredis
import json
try:
    from ..config import settings
    from ..auth import JWT_SECRET, JWT_ALGORITHM
except ImportError:
    from config import settings
    from auth import JWT_SECRET, JWT_ALGORITHM
from jose import jwt

router = APIRouter()


@router.websocket("/ws/{job_id}")
async def websocket_pipeline_progress(websocket: WebSocket, job_id: str, token: str = Query(None)):
    """
    WebSocket endpoint that streams pipeline progress from Redis pub/sub.
    Frontend connects with: ws://localhost:8000/ws/{job_id}
    """
    await websocket.accept()
    
    if not token:
        await websocket.close(code=1008)
        return
        
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        await websocket.close(code=1008)
        return
    
    # Create async Redis connection
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    
    # Subscribe to job's progress channel
    await pubsub.subscribe(f"job:{job_id}")
    
    # Ensure the pubsub connection is established before we enter the loop.
    await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
    
    # Send any existing logs from Redis list (for reconnection recovery)
    existing_logs = await r.lrange(f"job_logs:{job_id}", 0, -1)
    for log in existing_logs:
        try:
            await websocket.send_text(log)
        except Exception:
            break
    
    try:
        # Poll Redis pub/sub so the socket stays open even when there are gaps
        # between progress events.
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data_text = message["data"]
                await websocket.send_text(data_text)
                
                # Check for terminal events
                try:
                    data = json.loads(data_text)
                    if data.get("event") in ["pipeline_complete", "error"]:
                        break  # Close connection on completion
                except Exception:
                    pass

            await asyncio.sleep(0.1)
                    
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected from job {job_id}")
    except Exception as e:
        print(f"[WS] Error in websocket for job {job_id}: {e}")
    finally:
        await pubsub.unsubscribe(f"job:{job_id}")
        await r.aclose()
