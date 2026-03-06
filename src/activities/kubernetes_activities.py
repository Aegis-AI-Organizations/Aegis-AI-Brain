from temporalio import activity
from temporalio.exceptions import ApplicationError
import logging
import time

try:
    from kubernetes import client, config
except ImportError as exc:
    raise ImportError(
        "The 'kubernetes' package is required to use kubernetes_activities "
        "but could not be imported. Ensure it is installed and available."
    ) from exc

logger = logging.getLogger(__name__)


def _get_k8s_client() -> client.CoreV1Api:
    """Initializes and returns a Kubernetes CoreV1Api client."""
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def _create_namespace(k8s: client.CoreV1Api, namespace_name: str, scan_id: str):
    """Creates a namespace if it doesn't already exist."""
    ns_manifest = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace_name, labels={"aegis-scan": scan_id}
        )
    )
    try:
        k8s.create_namespace(body=ns_manifest)
        logger.debug(f"Created namespace: {namespace_name}")
    except client.rest.ApiException as e:
        if e.status == 409:
            logger.debug(f"Namespace {namespace_name} already exists.")
        else:
            logger.error(f"Failed to create namespace {namespace_name}: {e}")
            raise e


def _create_pod(
    k8s: client.CoreV1Api, namespace: str, pod_name: str, scan_id: str, image: str
):
    """Creates a pod in the specified namespace."""
    pod_manifest = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name, labels={"app": "vulnerable-target", "scan": scan_id}
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="target-container",
                    image=image,
                    image_pull_policy="IfNotPresent",
                    ports=[client.V1ContainerPort(container_port=80)],
                )
            ],
            restart_policy="Never",
        ),
    )
    try:
        k8s.create_namespaced_pod(namespace=namespace, body=pod_manifest)
        logger.debug(f"Created Pod {pod_name} in namespace {namespace}")
    except client.rest.ApiException as e:
        if e.status == 409:
            logger.debug(f"Pod {pod_name} already exists in {namespace}.")
        else:
            logger.error(f"Failed to create Pod {pod_name}: {e}")
            raise e


def _create_service(
    k8s: client.CoreV1Api, namespace: str, service_name: str, scan_id: str
):
    """Creates a service to expose the target pod."""
    svc_manifest = client.V1Service(
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            selector={"app": "vulnerable-target", "scan": scan_id},
            ports=[client.V1ServicePort(port=80, target_port=80)],
        ),
    )
    try:
        k8s.create_namespaced_service(namespace=namespace, body=svc_manifest)
        logger.debug(f"Created Service {service_name} in namespace {namespace}")
    except client.rest.ApiException as e:
        if e.status == 409:
            logger.debug(f"Service {service_name} already exists.")
        else:
            logger.error(f"Failed to create Service {service_name}: {e}")
            raise e


def _check_image_errors(pod: client.V1Pod):
    """Checks for ImagePullBackOff or other pull-related errors."""
    if pod.status.container_statuses:
        for status in pod.status.container_statuses:
            state = status.state.waiting
            if state and state.reason in [
                "ImagePullBackOff",
                "ErrImagePull",
                "InvalidImageName",
            ]:
                error_msg = f"Failed to deploy target: {state.reason} - {state.message}"
                logger.error(error_msg)
                raise ApplicationError(error_msg, non_retryable=True)


def _wait_for_pod_ready(
    k8s: client.CoreV1Api, namespace: str, pod_name: str, timeout: int = 60
):
    """Waits for the pod to reach the 'Ready' state."""
    start_time = time.time()
    logger.debug(f"Waiting for Pod {pod_name} to be Ready...")

    while time.time() - start_time < timeout:
        pod = k8s.read_namespaced_pod(name=pod_name, namespace=namespace)
        _check_image_errors(pod)

        is_ready = any(
            c.type == "Ready" and c.status == "True"
            for c in (pod.status.conditions or [])
        )

        if is_ready:
            logger.debug(f"Pod {pod_name} is Ready!")
            return

        time.sleep(2)

    raise Exception(f"Timeout: Pod {pod_name} did not become Ready within {timeout}s")


@activity.defn
def deploy_sandbox_target(scan_id: str, target_image: str) -> str:
    """
    Orchestrates the deployment of a sandbox environment for a scan.
    """
    k8s = _get_k8s_client()
    ns_name = f"aegis-war-room-{scan_id}"
    pod_name = f"target-{scan_id}"
    svc_name = f"svc-{scan_id}"

    _create_namespace(k8s, ns_name, scan_id)
    _create_pod(k8s, ns_name, pod_name, scan_id, target_image)
    _create_service(k8s, ns_name, svc_name, scan_id)

    _wait_for_pod_ready(k8s, ns_name, pod_name)

    return f"http://{svc_name}.{ns_name}.svc.cluster.local:80"


@activity.defn
def cleanup_sandbox(scan_id: str) -> str:
    """
    Cleans up the sandbox environment by deleting its namespace.
    """
    k8s = _get_k8s_client()
    ns_name = f"aegis-war-room-{scan_id}"

    try:
        k8s.delete_namespace(name=ns_name)
        logger.debug(f"Namespace {ns_name} deleted.")
    except client.rest.ApiException as e:
        if e.status == 404:
            logger.debug(f"Namespace {ns_name} already deleted.")
        else:
            logger.error(f"Error deleting namespace {ns_name}: {e}")
            return "FAILED"

    return "CLEANED"
