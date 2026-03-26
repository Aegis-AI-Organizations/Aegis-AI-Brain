import pytest
from unittest.mock import MagicMock, patch
from kubernetes import client
from activities.kubernetes_activities import (
    _get_k8s_client,
    _create_namespace,
    _create_pod,
    _create_service,
    _check_image_errors,
    deploy_sandbox_target,
    cleanup_sandbox,
)
from temporalio.exceptions import ApplicationError


@patch("kubernetes.config.load_incluster_config")
@patch("kubernetes.config.load_kube_config")
@patch("kubernetes.client.CoreV1Api")
def test_get_k8s_client_in_cluster(mock_api, mock_kube, mock_in_cluster):
    _get_k8s_client()
    mock_in_cluster.assert_called_once()
    mock_kube.assert_not_called()


@patch("kubernetes.config.load_incluster_config")
@patch("kubernetes.config.load_kube_config")
@patch("kubernetes.client.CoreV1Api")
def test_get_k8s_client_kube_config(mock_api, mock_kube, mock_in_cluster):
    from kubernetes.config.config_exception import ConfigException

    mock_in_cluster.side_effect = ConfigException("Not in cluster")
    _get_k8s_client()
    mock_kube.assert_called_once()


def test_create_namespace_success():
    mock_k8s = MagicMock()
    _create_namespace(mock_k8s, "test-ns", "scan-123")
    mock_k8s.create_namespace.assert_called_once()


def test_create_namespace_already_exists():
    mock_k8s = MagicMock()
    error = client.rest.ApiException(status=409)
    mock_k8s.create_namespace.side_effect = error
    _create_namespace(mock_k8s, "test-ns", "scan-123")  # Should not raise


def test_create_namespace_failure():
    mock_k8s = MagicMock()
    error = client.rest.ApiException(status=500)
    mock_k8s.create_namespace.side_effect = error
    with pytest.raises(client.rest.ApiException):
        _create_namespace(mock_k8s, "test-ns", "scan-123")


def test_create_pod_success():
    mock_k8s = MagicMock()
    _create_pod(mock_k8s, "ns", "pod", "scan", "img")
    mock_k8s.create_namespaced_pod.assert_called_once()


def test_create_pod_already_exists():
    mock_k8s = MagicMock()
    error = client.rest.ApiException(status=409)
    mock_k8s.create_namespaced_pod.side_effect = error
    _create_pod(mock_k8s, "ns", "pod", "scan", "img")  # Should not raise


def test_create_service_success():
    mock_k8s = MagicMock()
    _create_service(mock_k8s, "ns", "svc", "scan")
    mock_k8s.create_namespaced_service.assert_called_once()


def test_check_image_errors_pull_backoff():
    mock_pod = MagicMock()
    mock_status = MagicMock()
    mock_status.reason = "ImagePullBackOff"
    mock_status.message = "Err"
    mock_container_status = MagicMock()
    mock_container_status.state.waiting = mock_status
    mock_pod.status.container_statuses = [mock_container_status]

    with pytest.raises(ApplicationError) as excinfo:
        _check_image_errors(mock_pod)
    assert "ImagePullBackOff" in str(excinfo.value)


@patch("activities.kubernetes_activities._get_k8s_client")
@patch("activities.kubernetes_activities._create_namespace")
@patch("activities.kubernetes_activities._create_pod")
@patch("activities.kubernetes_activities._create_service")
@patch("activities.kubernetes_activities._wait_for_pod_ready")
def test_deploy_sandbox_target(mock_wait, mock_svc, mock_pod, mock_ns, mock_client):
    result = deploy_sandbox_target("scan-1", "img-1")
    assert "aegis-war-room-scan-1" in result
    mock_ns.assert_called_once()


@patch("activities.kubernetes_activities._get_k8s_client")
def test_cleanup_sandbox_success(mock_client):
    mock_k8s = MagicMock()
    mock_client.return_value = mock_k8s
    cleanup_sandbox("scan-1")
    mock_k8s.delete_namespace.assert_called_once()


@patch("activities.kubernetes_activities._get_k8s_client")
def test_cleanup_sandbox_not_found(mock_client):
    mock_k8s = MagicMock()
    mock_client.return_value = mock_k8s
    mock_k8s.delete_namespace.side_effect = client.rest.ApiException(status=404)
    res = cleanup_sandbox("scan-1")
    assert res == "CLEANED"
