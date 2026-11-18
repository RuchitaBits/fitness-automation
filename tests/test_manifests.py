from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
K8S = ROOT / "k8s"


def load_documents(name):
    with (K8S / name).open(encoding="utf-8") as manifest:
        return [document for document in yaml.safe_load_all(manifest) if document]


def find_document(documents, kind, name):
    return next(
        document
        for document in documents
        if document["kind"] == kind and document["metadata"]["name"] == name
    )


def test_all_kubernetes_manifests_parse_as_yaml():
    files = sorted(K8S.glob("*.yaml"))
    assert files
    for path in files:
        with path.open(encoding="utf-8") as manifest:
            documents = [document for document in yaml.safe_load_all(manifest) if document]
        assert documents, path.name
        assert all("apiVersion" in document and "kind" in document for document in documents)


def test_deployment_and_service_selectors_match_pod_labels():
    documents = [
        document
        for path in K8S.glob("*.yaml")
        for document in load_documents(path.name)
    ]
    deployments = [document for document in documents if document["kind"] == "Deployment"]
    services = [document for document in documents if document["kind"] == "Service"]

    for deployment in deployments:
        selector = deployment["spec"]["selector"]["matchLabels"]
        labels = deployment["spec"]["template"]["metadata"]["labels"]
        assert all(labels.get(key) == value for key, value in selector.items())

    for service in services:
        selector = service["spec"].get("selector", {})
        assert selector, service["metadata"]["name"]
        assert any(
            all(
                deployment["spec"]["template"]["metadata"]["labels"].get(key) == value
                for key, value in selector.items()
            )
            for deployment in deployments
        ), service["metadata"]["name"]


def test_blue_green_service_selectors_match_each_color():
    service = load_documents("service.yaml")[0]
    selector = service["spec"]["selector"].copy()
    selector.pop("app.kubernetes.io/track")
    for color in ("blue", "green"):
        deployment = load_documents(f"deployment-{color}.yaml")[0]
        template_labels = deployment["spec"]["template"]["metadata"]["labels"]
        assert all(template_labels[key] == value for key, value in selector.items())
        assert template_labels["app.kubernetes.io/track"] == color


def test_canary_virtual_service_routes_real_weighted_traffic():
    documents = load_documents("canary.yaml")
    destination_rule = find_document(documents, "DestinationRule", "aceest-canary")
    virtual_service = find_document(documents, "VirtualService", "aceest-canary")
    subset_names = {item["name"] for item in destination_rule["spec"]["subsets"]}
    routes = virtual_service["spec"]["http"][0]["route"]

    assert {route["destination"]["subset"] for route in routes} == subset_names
    assert sum(route["weight"] for route in routes) == 100
    assert sorted(route["weight"] for route in routes) == [10, 90]


def test_shadow_traffic_is_mirrored_to_an_isolated_safe_copy():
    documents = load_documents("shadow.yaml")
    virtual_service = find_document(documents, "VirtualService", "aceest-shadow")
    shadow_deployment = find_document(documents, "Deployment", "aceest-shadow-copy")
    shadow_service = find_document(documents, "Service", "aceest-shadow-copy")
    request_route = virtual_service["spec"]["http"][0]
    shadow_container = shadow_deployment["spec"]["template"]["spec"]["containers"][0]
    shadow_environment = {item["name"]: item.get("value") for item in shadow_container["env"]}

    assert request_route["mirror"]["host"] == shadow_service["metadata"]["name"]
    assert request_route["mirrorPercentage"]["value"] == 100.0
    assert shadow_environment["SHADOW_MODE"] == "true"
    assert shadow_deployment["spec"]["template"]["spec"]["volumes"][0]["emptyDir"] == {}


def test_ab_route_uses_beta_header_and_has_a_control_route():
    documents = load_documents("ab-testing.yaml")
    virtual_service = find_document(documents, "VirtualService", "aceest-ab")
    routes = virtual_service["spec"]["http"]
    beta = routes[0]
    control = routes[1]

    assert beta["match"][0]["headers"]["x-aceest-group"]["exact"] == "beta"
    assert beta["route"][0]["destination"]["subset"] == "b"
    assert control["route"][0]["destination"]["subset"] == "a"


def test_rolling_update_and_persistent_storage_are_configured():
    documents = load_documents("rolling-update.yaml")
    deployment = find_document(documents, "Deployment", "aceest-rolling")
    service = find_document(documents, "Service", "aceest-rolling-service")
    pod_spec = deployment["spec"]["template"]["spec"]
    selector = service["spec"]["selector"]
    labels = deployment["spec"]["template"]["metadata"]["labels"]

    assert deployment["spec"]["strategy"]["rollingUpdate"] == {
        "maxUnavailable": 0,
        "maxSurge": 1,
    }
    assert all(labels[key] == value for key, value in selector.items())
    assert any(volume.get("persistentVolumeClaim", {}).get("claimName") == "aceest-data" for volume in pod_spec["volumes"])
    assert deployment["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]


def test_deployments_use_a_real_image_tag_and_secret_references():
    for path in K8S.glob("*.yaml"):
        for document in load_documents(path.name):
            if document["kind"] != "Deployment":
                continue
            for container in document["spec"]["template"]["spec"]["containers"]:
                assert container["image"] == "aceest-fitness:3.2.4"
                env_names = {item["name"] for item in container.get("env", [])}
                if document["metadata"]["name"] != "aceest-shadow-copy":
                    assert {"ADMIN_USERNAME", "ADMIN_PASSWORD", "FLASK_SECRET_KEY"} <= env_names
