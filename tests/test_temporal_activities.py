from types import SimpleNamespace

import pytest
from temporalio.api.enums.v1.task_queue_pb2 import TASK_QUEUE_TYPE_ACTIVITY
from temporalio.testing import ActivityEnvironment

from activities.temporal_activities import check_task_queue_pollers


class _WorkflowService:
    def __init__(self):
        self.request = None

    async def describe_task_queue(self, request):
        self.request = request
        return SimpleNamespace(pollers=[object()])


@pytest.mark.asyncio
async def test_check_task_queue_pollers_describes_activity_queue(monkeypatch):
    service = _WorkflowService()
    client = SimpleNamespace(workflow_service=service)
    monkeypatch.setattr(
        "activities.temporal_activities.get_temporal_client", lambda: client
    )

    activity_env = ActivityEnvironment()
    result = await activity_env.run(check_task_queue_pollers, "CREWAI_TASK_QUEUE")

    assert result is True
    assert service.request.task_queue.name == "CREWAI_TASK_QUEUE"
    assert service.request.task_queue_type == TASK_QUEUE_TYPE_ACTIVITY
