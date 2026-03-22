"""WebSocket endpoint for real-time event streaming.

Connects to the in-process event bus and broadcasts pipeline events
to connected WebSocket clients (e.g., PixiJS frontend).
"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.event_bus import Event, event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that streams pipeline events in real-time."""
    await websocket.accept()

    async def send_event(event: Event):
        """Handler that sends events to this WebSocket client."""
        try:
            await websocket.send_text(json.dumps(event.to_dict()))
        except Exception:
            pass

    # Subscribe to all events
    event_bus.subscribe_all(send_event)

    try:
        # Send event history on connect
        history = event_bus.get_history(limit=20)
        await websocket.send_text(json.dumps({
            "type": "connection.established",
            "data": {"history": history},
        }))

        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe_all_handler(send_event)
