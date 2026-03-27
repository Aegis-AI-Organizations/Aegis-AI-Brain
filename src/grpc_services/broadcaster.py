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

    def broadcast(self, scan_id, status):
        loop = asyncio.get_event_loop()
        for q in self.queues:
            loop.call_soon_threadsafe(q.put_nowait, (scan_id, status))


broadcaster = StatusBroadcaster()
