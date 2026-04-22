import asyncio


class StatusBroadcaster:
    def __init__(self):
        self.queues = set()

    def register(self):
        q = asyncio.Queue()
        self.queues.add(q)
        return q

    def unregister(self, q):
        self.queues.remove(q)

    def broadcast(self, event_type, data):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Fallback for threads without an event loop
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
            except Exception:
                return

        for q in self.queues:
            loop.call_soon_threadsafe(q.put_nowait, (event_type, data))


broadcaster = StatusBroadcaster()
