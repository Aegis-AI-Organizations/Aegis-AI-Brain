from temporalio import activity
from temporalio.api.enums.v1.task_queue_pb2 import TASK_QUEUE_TYPE_ACTIVITY
from temporalio.api.taskqueue.v1 import TaskQueue
from temporalio.api.workflowservice.v1 import DescribeTaskQueueRequest

from config.config import TEMPORAL_NAMESPACE
from services.temporal_client_holder import get_temporal_client


@activity.defn
async def check_task_queue_pollers(task_queue: str) -> bool:
    client = get_temporal_client()
    response = await client.workflow_service.describe_task_queue(
        DescribeTaskQueueRequest(
            namespace=TEMPORAL_NAMESPACE,
            task_queue=TaskQueue(name=task_queue),
            task_queue_type=TASK_QUEUE_TYPE_ACTIVITY,
        )
    )
    return len(response.pollers) > 0
