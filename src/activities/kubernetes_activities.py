from temporalio import activity
import logging

try:
    from kubernetes import client, config
except ImportError as exc:
    raise ImportError(
        "The 'kubernetes' package is required to use kubernetes_activities "
        "but could not be imported. Ensure it is installed and available."
    ) from exc

logger = logging.getLogger(__name__)


def _get_k8s_client():
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

    return client.CoreV1Api()


@activity.defn
def deploy_sandbox_target(scan_id: str, target_image: str) -> str:
    """
    Deploys the vulnerable target image in a dedicated sandbox namespace.
    Returns the internal ClusterIP DNS name of the deployed service.
    """
    k8s = _get_k8s_client()
    namespace_name = f"sandbox-{scan_id}"

    ns_manifest = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace_name, labels={"aegis-scan": scan_id}
        )
    )

    try:
        k8s.create_namespace(body=ns_manifest)
        logger.info(f"Creation of namespace {namespace_name}")
    except Exception as e:
        logger.warning(f"Namespace {namespace_name} may already exist: {e}")

    pod_name = f"target-{scan_id}"
    pod_manifest = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=pod_name, labels={"app": "vulnerable-target", "scan": scan_id}
        ),
        spec=client.V1PodSpec(
            containers=[
                client.V1Container(
                    name="target-container",
                    image=target_image,
                    ports=[client.V1ContainerPort(container_port=80)],
                )
            ],
            restart_policy="Never",
        ),
    )

    logger.info(f"Deployment of Pod {pod_name} ({target_image})")
    k8s.create_namespaced_pod(namespace=namespace_name, body=pod_manifest)

    service_name = f"svc-{scan_id}"
    svc_manifest = client.V1Service(
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            selector={"app": "vulnerable-target", "scan": scan_id},
            ports=[client.V1ServicePort(port=80, target_port=80)],
        ),
    )

    logger.info(f"Creation of Service {service_name}")
    k8s.create_namespaced_service(namespace=namespace_name, body=svc_manifest)

    target_endpoint = f"http://{service_name}.{namespace_name}.svc.cluster.local:80"
    return target_endpoint


@activity.defn
def cleanup_sandbox(scan_id: str) -> str:
    """
    Deletes the sandbox namespace, effectively terminating the target Pod and Service.
    """
    k8s = _get_k8s_client()
    namespace_name = f"sandbox-{scan_id}"

    logger.info(f"Deletion of namespace {namespace_name}")
    try:
        k8s.delete_namespace(name=namespace_name)
    except Exception as e:
        logger.error(f"Error during deletion of {namespace_name}: {e}")
        return "FAILED"

    return "CLEANED"
