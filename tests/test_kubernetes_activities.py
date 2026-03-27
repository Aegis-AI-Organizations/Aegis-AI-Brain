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
def test_cleanup_sandbox_already_gone(mock_get_client):
    mock_k8s = MagicMock()
    mock_get_client.return_value = mock_k8s
    mock_k8s.delete_namespace.side_effect = client.rest.ApiException(status=404)

    result = cleanup_sandbox("scan-1")
    assert result == "CLEANED"
