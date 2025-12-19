# backend/app/websocket_handler.py
import json
import asyncio
from typing import Dict, Set, Any, Optional, AsyncIterator
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from sqlmodel import Session
from app.db import get_session
from app.finance_agent import get_finance_agent

# -------------------------
# Pydantic message schemas
# -------------------------
class ChatMessage(BaseModel):
    type: str
    content: str

class TypingMessage(BaseModel):
    type: str

class ClearHistoryMessage(BaseModel):
    type: str

# Union-ish helper: we will validate based on `type` field
MESSAGE_TYPES = {"chat", "typing", "clear_history", "ping"}

# -------------------------
# Utilities
# -------------------------
def now_ts() -> float:
    """Return event-loop time for timestamps"""
    return asyncio.get_event_loop().time()

# -------------------------
# Connection Manager
# -------------------------
class ConnectionManager:
    """Manages websocket connections (multiple sockets per user) and AI interactions"""
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # user_id -> set of websockets
        # Initialize finance agent (which internally wraps Gemini AI)
        try:
            self.agent = get_finance_agent()  # should return an object with process_query(), clear_conversation_history(), analyze_data_patterns(), etc.
        except Exception as e:
            print(f"Warning: Could not initialize Finance Agent: {e}")
            self.agent = None

        # Lock to protect concurrent send/remove operations for a user's set
        self._lock = asyncio.Lock()

    # --- connection management ---
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        # welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to Savion Smart Finance Assistant.",
            "timestamp": now_ts()
        }, websocket)
        print(f"Client connected for user {user_id}. Total sockets: {self.get_connection_count(user_id)}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        print(f"Client disconnected for user {user_id}. Remaining sockets: {self.get_connection_count(user_id)}")

    # --- message sending helpers ---
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send JSON message to a single socket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending personal message: {e}")

    async def send_message_to_user(self, message: dict, user_id: str):
        """Send JSON message to all sockets for a user (safe copy of set)"""
        async with self._lock:
            connections = set(self.active_connections.get(user_id, set()))
        for ws in connections:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                # best-effort cleanup
                await self._safe_remove(ws, user_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected users"""
        async with self._lock:
            all_conns = [ws for conns in self.active_connections.values() for ws in conns]
        for ws in all_conns:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print("Broadcast send error:", e)

    async def _safe_remove(self, websocket: WebSocket, user_id: str):
        """Remove a websocket safely (helper for error cases)"""
        try:
            await self.disconnect(websocket, user_id)
        except Exception:
            # swallow safe remove errors
            pass

    # --- high-level handlers ---
    async def handle_message(self, websocket: WebSocket, user_id: str, message_json: dict):
        """Dispatch incoming message to a handler after validation"""
        # Validate 'type'
        msg_type = message_json.get("type")
        if msg_type not in MESSAGE_TYPES:
            await self.send_personal_message({"type": "error", "message": f"Unknown message type: {msg_type}"}, websocket)
            return

        try:
            if msg_type == "chat":
                msg = ChatMessage(**message_json)
                await self.handle_chat_message(websocket, user_id, msg.content)
            elif msg_type == "typing":
                msg = TypingMessage(**message_json)
                await self.handle_typing_indicator(websocket, user_id)
            elif msg_type == "clear_history":
                msg = ClearHistoryMessage(**message_json)
                await self.handle_clear_history(websocket, user_id)
            elif msg_type == "ping":
                await self.send_personal_message({"type": "pong", "timestamp": now_ts()}, websocket)
            else:
                await self.send_personal_message({"type": "error", "message": "Unhandled message type."}, websocket)
        except ValidationError as ve:
            await self.send_personal_message({"type": "error", "message": "Invalid message format.", "details": ve.errors()}, websocket)
        except Exception as e:
            print("handle_message error:", e)
            await self.send_personal_message({"type": "error", "message": f"Server error: {e}"}, websocket)

    async def handle_typing_indicator(self, websocket: WebSocket, user_id: str):
        """Optionally broadcast typing indicator to other sockets of same user (or skip)"""
        # Broadcast "user typing" to other sockets of the same user (not to the origin socket)
        async with self._lock:
            conns = set(self.active_connections.get(user_id, set()))
        for ws in conns:
            if ws is not websocket:
                try:
                    await ws.send_text(json.dumps({"type": "typing", "user_id": user_id, "timestamp": now_ts()}))
                except Exception as e:
                    print("typing indicator send error:", e)

    async def handle_clear_history(self, websocket: WebSocket, user_id: str):
        """Clear conversation history for the user in the agent"""
        if not self.agent:
            await self.send_personal_message({"type": "error", "message": "AI agent not configured."}, websocket)
            return
        try:
            self.agent.clear_conversation_history(user_id)
            await self.send_personal_message({"type": "history_cleared", "message": "Conversation history cleared."}, websocket)
        except Exception as e:
            print("clear_history error:", e)
            await self.send_personal_message({"type": "error", "message": f"Could not clear history: {e}"}, websocket)

    async def handle_chat_message(self, websocket: WebSocket, user_id: str, content: str):
        """Main chat handler: show typing, run AI (or fallback), return result & insights"""
        if not content or not content.strip():
            return

        # Notify the client that AI is thinking
        await self.send_personal_message({"type": "typing", "message": "AI is thinking...", "timestamp": now_ts()}, websocket)

        # Use DB session and call the agent
        try:
            # get DB session from generator: get_session() yields a Session; use next() to get it
            session: Session = next(get_session())

            # If agent available, ask it to process the query.
            if self.agent and getattr(self.agent, "process_query", None):
                # If agent's process_query is async, call directly; else run in executor
                process = self.agent.process_query
                if asyncio.iscoroutinefunction(process):
                    ai_result = await process(user_id, content, session)
                else:
                    loop = asyncio.get_event_loop()
                    ai_result = await loop.run_in_executor(None, lambda: process(user_id, content, session))
            else:
                # fallback response (no AI)
                ai_result = {
                    "type": "fallback_response",
                    "query": content,
                    "response": "I can help with basic analysis. To enable AI-powered insights, please configure the Gemini API key.",
                    "insights": ["agent_not_configured"],
                    "user_context_summary": {"ai_available": False}
                }

            # Normalize result (ensure dictionary & keys)
            if isinstance(ai_result, str):
                # if agent returned just text
                response_text = ai_result
                insights = []
                user_ctx = {}
            elif isinstance(ai_result, dict):
                response_text = ai_result.get("response", "")
                insights = ai_result.get("insights", [])
                user_ctx = ai_result.get("user_context_summary", {})
            else:
                # unexpected type
                response_text = str(ai_result)
                insights = []
                user_ctx = {}

            # If agent returned a stream generator, try to stream it
            # (This is optional and only used if your agent/model exposes streaming)
            streamed = False
            if self.agent and getattr(self.agent, "stream_response", None):
                try:
                    stream_fn = getattr(self.agent, "stream_response")
                    # If generator is async iterator
                    if asyncio.iscoroutinefunction(stream_fn):
                        # async generator function - call and iterate
                        async for chunk in stream_fn(user_id, content, session):
                            await self.send_personal_message({"type": "ai_stream", "chunk": chunk, "timestamp": now_ts()}, websocket)
                        streamed = True
                    else:
                        # sync generator - run in executor
                        loop = asyncio.get_event_loop()
                        def run_stream():
                            for chunk in stream_fn(user_id, content, session):
                                # yield chunks back to event loop via queue: but for simplicity, return list
                                yield chunk
                        chunks = await loop.run_in_executor(None, lambda: list(run_stream()))
                        for chunk in chunks:
                            await self.send_personal_message({"type": "ai_stream", "chunk": chunk, "timestamp": now_ts()}, websocket)
                        streamed = True
                except Exception as e:
                    # If streaming fails - fall back to sending full response
                    print("Streaming failed or not supported:", e)
                    streamed = False

            # If not streamed, send the complete response
            if not streamed:
                await self.send_personal_message({
                    "type": "ai_response",
                    "query": content,
                    "response": response_text,
                    "insights": insights,
                    "user_context": user_ctx,
                    "timestamp": now_ts()
                }, websocket)

        except Exception as e:
            print("Error in handle_chat_message:", e)
            await self.send_personal_message({"type": "error", "message": f"Server error while processing chat: {e}"}, websocket)

    # --- push helpers for external code to call ---
    async def send_notification(self, user_id: str, notification: dict):
        """Send a push notification to a user (external systems call this)"""
        await self.send_message_to_user({"type": "notification", **notification, "timestamp": now_ts()}, user_id)

    async def send_data_analysis(self, user_id: str, analysis: dict):
        """Send completed data analysis results to a user"""
        await self.send_message_to_user({"type": "data_analysis", "analysis": analysis, "timestamp": now_ts()}, user_id)

    # --- introspection utilities ---
    def get_connection_count(self, user_id: str) -> int:
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        return sum(len(s) for s in self.active_connections.values())

    def get_connected_users(self) -> list:
        return list(self.active_connections.keys())


# Global manager instance
manager = ConnectionManager()

# -------------------------
# WebSocket endpoint helper
# -------------------------
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Entry point to be used by your FastAPI route.
    Example in main.py:
        @app.websocket("/ws/{user_id}")
        async def ws_route(websocket: WebSocket, user_id: str):
            await websocket_endpoint(websocket, user_id)
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal_message({"type": "error", "message": "Invalid JSON"}, websocket)
                continue
            await manager.handle_message(websocket, user_id, message)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        print(f"User {user_id} disconnected from WebSocket")
    except Exception as e:
        print(f"Unexpected WebSocket error for user {user_id}: {e}")
        await manager.disconnect(websocket, user_id)
