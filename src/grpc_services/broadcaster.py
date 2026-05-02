import asyncio


class StatusBroadcaster:
    def __init__(self):
        self.queues = set()
        self.loop = None

    def register(self):
        if self.loop is None:
            self.loop = asyncio.get_running_loop()
        q = asyncio.Queue()
        self.queues.add(q)
        return q

    def unregister(self, q):
        self.queues.remove(q)

    def broadcast(self, event_type, data):
        if not self.loop:
            return
        for q in self.queues:
            self.loop.call_soon_threadsafe(q.put_nowait, (event_type, data))


broadcaster = StatusBroadcaster()
