import pytest
from temporalio.exceptions import ApplicationError
from unittest.mock import MagicMock, patch
from kubernetes import client
from activities.kubernetes_activities import deploy_sandbox_target, cleanup_sandbox


@patch("activities.kubernetes_activities._get_k8s_client")
def test_deploy_sandbox_target_success(mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s

    # Mock namespace creation (ignore)
    # Mock pod creation (ignore)
    # Mock service creation (ignore)

    # Mock pod ready check
    mock_pod = MagicMock()
    mock_pod.status.conditions = [MagicMock(type="Ready", status="True")]
    mock_k8s.read_namespaced_pod.return_value = mock_pod

    url = deploy_sandbox_target("scan-1", "nginx")
    assert "aegis-war-room-scan-1" in url
    assert "svc-scan-1" in url


@patch("activities.kubernetes_activities._get_k8s_client")
def test_cleanup_sandbox_success(mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s

    result = cleanup_sandbox("scan-1")
    assert result == "CLEANED"
    mock_k8s.delete_namespace.assert_called_once_with(name="aegis-war-room-scan-1")


@patch("activities.kubernetes_activities._get_k8s_client")
def test_deploy_sandbox_target_image_pull_error(mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s

    # Mock pod check with error
    mock_pod = MagicMock()
    mock_status = MagicMock()
    mock_status.state.waiting.reason = "ImagePullBackOff"
    mock_status.state.waiting.message = "Pull failed"
    mock_pod.status.container_statuses = [mock_status]
    mock_k8s.read_namespaced_pod.return_value = mock_pod

    with pytest.raises(ApplicationError, match="ImagePullBackOff"):
        deploy_sandbox_target("scan-1", "nginx")


@patch("activities.kubernetes_activities._get_k8s_client")
@patch("activities.kubernetes_activities.time.sleep", return_value=None)
@patch("activities.kubernetes_activities.time.time")
def test_deploy_sandbox_target_timeout(mock_time, mock_sleep, mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s
    mock_time.side_effect = [0, 10, 20, 100]  # Trigger timeout

    mock_pod = MagicMock()
    mock_pod.status.conditions = []
    mock_pod.status.container_statuses = []
    mock_k8s.read_namespaced_pod.return_value = mock_pod

    with pytest.raises(Exception, match="Timeout"):
        deploy_sandbox_target("scan-1", "nginx")


@patch("activities.kubernetes_activities.config")
def test_get_k8s_client_incluster_fallback(mock_config):
    mock_config.config_exception.ConfigException = Exception
    mock_config.load_incluster_config.side_effect = Exception("Not in cluster")

    from activities.kubernetes_activities import _get_k8s_client

    with patch("activities.kubernetes_activities.client.CoreV1Api") as mock_api:
        _get_k8s_client()
        mock_config.load_kube_config.assert_called_once()
        mock_api.assert_called_once()


@patch("activities.kubernetes_activities._get_k8s_client")
def test_cleanup_sandbox_failure(mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s
    mock_k8s.delete_namespace.side_effect = client.rest.ApiException(status=500)

    result = cleanup_sandbox("scan-1")
    assert result == "FAILED"
