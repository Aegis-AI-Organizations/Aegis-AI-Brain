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
        for q in self.queues:
            q.put_nowait((scan_id, status))


broadcaster = StatusBroadcaster()
