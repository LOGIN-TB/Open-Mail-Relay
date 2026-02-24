"""
Singleton log broadcaster: one Docker log reader thread, N WebSocket subscribers.
"""
import asyncio
import logging
import re
import threading
from collections import deque

from app.services.docker_service import get_mail_container

logger = logging.getLogger(__name__)

# Log lines matching any of these patterns are suppressed (noise)
_NOISE_PATTERNS = [
    re.compile(r"postfix/postfix-script\[\d+\]: the Postfix mail system is running"),
    re.compile(r"postfix/postfix-script\[\d+\]: refreshing the Postfix mail system"),
]


class LogBroadcaster:
    def __init__(self):
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Keep last 50 lines as backlog for new subscribers
        self._backlog: deque[str] = deque(maxlen=50)

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        with self._lock:
            # Send backlog to new subscriber
            for line in self._backlog:
                try:
                    q.put_nowait(line)
                except asyncio.QueueFull:
                    break
            self._subscribers.add(q)
            # Start reader if this is the first subscriber
            if self._reader_thread is None or not self._reader_thread.is_alive():
                self._stop.clear()
                self._reader_thread = threading.Thread(
                    target=self._read_loop, daemon=True, name="log-broadcaster"
                )
                self._reader_thread.start()
                logger.info("Log broadcaster started")
        return q

    def unsubscribe(self, q: asyncio.Queue[str]):
        with self._lock:
            self._subscribers.discard(q)
            # Stop reader if no more subscribers
            if not self._subscribers:
                self._stop.set()
                logger.info("Log broadcaster stopping (no subscribers)")

    def _read_loop(self):
        while not self._stop.is_set():
            try:
                container = get_mail_container()
                if container is None:
                    logger.warning("Log broadcaster: container not found, retrying in 10s")
                    self._stop.wait(10)
                    continue

                stream = container.logs(stream=True, follow=True, tail=50, timestamps=True)
                for chunk in stream:
                    if self._stop.is_set():
                        break
                    line = chunk.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    # Filter out noise
                    if any(p.search(line) for p in _NOISE_PATTERNS):
                        continue

                    with self._lock:
                        self._backlog.append(line)
                        dead: list[asyncio.Queue] = []
                        for q in self._subscribers:
                            try:
                                q.put_nowait(line)
                            except asyncio.QueueFull:
                                # Slow consumer — drop oldest, push new
                                try:
                                    q.get_nowait()
                                    q.put_nowait(line)
                                except Exception:
                                    dead.append(q)
                            except Exception:
                                dead.append(q)
                        for q in dead:
                            self._subscribers.discard(q)

            except Exception as e:
                if not self._stop.is_set():
                    logger.error(f"Log broadcaster error: {e}")
                    self._stop.wait(5)

    def stop(self):
        self._stop.set()
        with self._lock:
            self._subscribers.clear()


# Module-level singleton
broadcaster = LogBroadcaster()
