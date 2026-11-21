# ACEest Fitness & Gym - DevOps Assignment 2 Report

## Project overview

ACEest Fitness & Gym is a Flask application for staff to manage clients, fitness programs, workouts, membership details, and progress. Assignment 2 extends the Assignment 1 web application with automated validation, coverage reporting, container builds, code-quality analysis configuration, and Kubernetes deployment examples. The existing Flask UI, templates, styles, and application workflows are retained.

## Objectives

- Preserve the Assignment 1 application and its Git history.
- Automate syntax, lint, test, and coverage checks.
- Define Jenkins and GitHub Actions CI workflows.
- Package separate test and runtime Docker images.
- Configure SonarQube analysis and a quality gate.
- Describe Docker Hub publishing and Minikube deployment.
- Demonstrate rolling update, rollback, and additional traffic strategies.
- Document which checks were run locally and which require external services.

## Architecture

```text
GitHub main
  -> GitHub Actions / Jenkins
  -> Python syntax, Ruff, Pytest, and coverage
  -> SonarQube analysis and Quality Gate (Jenkins)
  -> Docker runtime and test images
  -> Optional Docker Hub image publishing
  -> Kubernetes Deployments and Services
  -> Health probes, rollout status, and rollback
```

The Flask app serves its browser interface from `templates/` and `static/`, uses SQLite for application data, and exposes `/health`. The Kubernetes examples use a persistent volume claim. SQLite with a `ReadWriteOnce` claim is intended for the single-node Minikube demonstration; it is not a substitute for a production multi-node database.

## Tools and technologies

- Python 3.12 project target, Flask, SQLite, and Gunicorn
- Pytest, pytest-cov, Ruff, and PyYAML
- Git and GitHub
- GitHub Actions and Jenkins
- SonarQube
- Docker and Docker Hub
- Kubernetes, Minikube, and Istio-compatible routing examples
- Windows PowerShell deployment helpers

## CI/CD implementation

GitHub Actions runs syntax validation, Ruff, Pytest, runtime image build, container tests, and a runtime health check. Docker jobs depend on the lint/test job so packaging is gated on those checks.

The existing Jenkinsfile contains the following ordered stages:

1. Checkout; choose the supplied `IMAGE_VERSION` or `VERSION`, and record the commit SHA.
2. Set up Python and install `requirements-dev.txt`.
3. Compile the app/tests and run Ruff.
4. Run Pytest and write JUnit results.
5. Generate XML/HTML coverage.
6. Run SonarQube analysis and wait for the Quality Gate.
7. Build the versioned runtime image and test image; run container tests.
8. When `PUBLISH_IMAGE=true`, use Jenkins credential `dockerhub-creds` to authenticate, tag by version and commit SHA, and push both tags to `IMAGE_REPO`.
9. When `DEPLOY_TO_K8S=true`, require publishing, use Jenkins credential `kubeconfig`, deploy the pushed image, roll back if the update fails, and verify rollout and Service status.

The Jenkins agent must be labelled `linux-docker` and provide Python 3 with `venv`/`pip`, Git, Docker CLI/daemon access, `sonar-scanner` on `PATH`, and `kubectl` when deployment is enabled. Configure the SonarQube server as `sonarqube`, install the SonarQube Scanner, Credentials Binding, Pipeline, Git, and JUnit plugins, and configure the SonarQube webhook to `<JENKINS_URL>/sonarqube-webhook/`. Docker Pipeline is not required because the Jenkinsfile uses the Docker CLI. External Jenkins/plugin/credential configuration and execution remain unverified in this environment.

**Jenkins was not available for execution during this audit.** Configure the `linux-docker` agent, SonarQube server name, Jenkins plugins, and required credentials before running the pipeline.

Evidence placeholder (replace only with a real captured result):
`[Screenshot placeholder: Jenkins build stages and final result]`

## Pytest and coverage

Run locally with:

```powershell
python -m compileall -q app.py tests
python -m ruff check app.py tests
python -m pytest -q
python -m pytest -q --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html --cov-report=term-missing
```

Local audit execution on Windows with Python 3.14.8: **23 tests passed; application coverage was 90%**. The configured CI target is Python 3.12; that interpreter was not available locally. Generated coverage artifacts are ignored by Git.

Evidence placeholder (replace only with a real captured result):
`[Screenshot placeholder: Pytest summary and coverage report]`

## SonarQube analysis

`sonar-project.properties` scopes analysis to `app.py` and `tests/`, sets Python 3.12, and points to the generated `coverage.xml`. Jenkins runs the scanner with the configured SonarQube server and waits for its Quality Gate.

SonarQube server/scanner execution and the Quality Gate were **not verified** in this environment. No scan result or quality score is claimed.

Evidence placeholder (replace only with a real captured result):
`[Screenshot placeholder: SonarQube project analysis and Quality Gate]`

## Docker and Docker Hub

The Dockerfile defines a test stage and a smaller non-root runtime stage. The runtime exposes port 5000, stores SQLite data under `/data`, and defines a `/health` container check. Docker and its daemon were unavailable during this audit, so image builds, container startup, and health checks were **not verified**.

Jenkins can tag the runtime image with the configured version and commit SHA, authenticate using the Jenkins Docker Hub credential, and push both tags. Docker Hub namespace, credentials, and image availability were **not verified**.

Evidence placeholders (replace only with real captured results):

- `[Screenshot placeholder: Docker runtime image build]`
- `[Screenshot placeholder: Container startup and /health response]`
- `[Screenshot placeholder: Docker Hub repository and pushed tags]`

## Kubernetes deployment and Service

The rolling manifest defines the `aceest-rolling` Deployment and its `aceest-rolling-service` ClusterIP Service. The Deployment has matching selectors, three replicas, resource settings, startup/readiness/liveness HTTP probes, persistent storage, and a rolling update strategy. Blue-green resources use a separate `aceest-service`. Credentials are referenced through Kubernetes Secret keys; no Secret values are stored in the repository.

The manifest files parse as YAML, and local tests check Deployment/Service selector consistency and image references. `kubectl` and Minikube were unavailable, so API-server validation, cluster scheduling, PVC behavior, probes, Service endpoints, and live deployment were **not verified**.

For the local single-node demonstration, build and load the runtime image, create the `aceest-secrets` Secret through the cluster, then apply `k8s/pvc.yaml` and `k8s/rolling-update.yaml`. Use `kubectl port-forward service/aceest-rolling-service 18080:80` to test `/health`. Do not apply the blue-green Service to the rolling deployment.

Evidence placeholders (replace only with real captured results):

- `[Screenshot placeholder: Minikube Pods, Deployments, PVC, and Services]`
- `[Screenshot placeholder: Application health through the Kubernetes Service]`

## Rolling updates and rollback

The rolling Deployment specifies `maxUnavailable: 0`, `maxSurge: 1`, and a revision history limit. A new image can be applied with `kubectl set image`; check progress and revision history with `kubectl rollout status` and `kubectl rollout history`. Roll back with `kubectl rollout undo` and verify the restored rollout.

Manifest structure and the configured strategy were **verified by local tests**; update and rollback behavior against a live cluster were **not verified**.

Evidence placeholders (replace only with real captured results):

- `[Screenshot placeholder: Successful rolling update and ready Pods]`
- `[Screenshot placeholder: Rollout history and successful rollback]`

## Monitoring and logging

The application health endpoint performs a SQLite connectivity check. Docker's health check and Kubernetes HTTP probes use `/health`. Gunicorn writes access and error logs to standard output/error, which can be inspected with container logs or `kubectl logs`. The README documents common inspection commands.

This repository does not include Prometheus, Grafana, centralized log aggregation, alerting, or a metrics dashboard. Live health probes and log collection were **not verified**.

Evidence placeholder (replace only with a real captured result):
`[Screenshot placeholder: Pod health and application logs]`

## Deployment strategies

- **Rolling update:** native Kubernetes rolling strategy; manifest and selector checks pass locally. Live execution is pending.
- **Blue-green:** separate blue/green Deployments and a Service track switch helper. Manifests and local script syntax were checked; live traffic switching is pending.
- **Canary:** Istio DestinationRule/VirtualService examples define 90/10 routing and a helper to change weights. This requires Istio or a compatible service mesh; live routing is pending.
- **Shadow:** Istio mirroring sends requests to a separate copy. The app's shadow mode rejects state-changing requests, and local tests verify those writes are not persisted. Live mesh mirroring is pending.
- **A/B:** Istio header routing sends `x-aceest-group: beta` traffic to variant B and default traffic to A. Manifest structure was checked; live routing is pending.

Evidence placeholders (replace only with real captured results):

- `[Screenshot placeholder: Blue-green Service selector switch]`
- `[Screenshot placeholder: Istio canary traffic weights]`
- `[Screenshot placeholder: Shadow mirror and isolated copy]`
- `[Screenshot placeholder: A/B header-based routing]`

## Requirement status

| Assignment requirement | Status | Audit note |
|---|---|---|
| GitHub version control | Implemented and verified | Existing `main` and Assignment 1 history are preserved. |
| Jenkins CI/CD | Implemented but not verified | Pipeline and credentials are configured by reference; Jenkins execution is pending. |
| Automated Pytest | Implemented and verified | Local suite executed; see the result above. |
| SonarQube analysis | Implemented but not verified | Configuration and pipeline stage exist; scanner/server unavailable. |
| Coverage reporting | Implemented and verified | Local coverage generated; percentage recorded above. |
| Docker containerization | Implemented but not verified | Test/runtime stages reviewed; Docker unavailable. |
| Docker Hub integration | Implemented but not verified | Jenkins publishing is opt-in and credential-backed; no push verified. |
| Minikube deployment | Implemented but not verified | Manifests exist; Minikube and `kubectl` unavailable. |
| Kubernetes Service | Implemented but not verified | Service resources and selectors checked locally; no cluster endpoints verified. |
| Rolling updates | Implemented but not verified | Strategy settings checked; no live rollout run. |
| Rollback | Implemented but not verified | Jenkins and PowerShell commands exist; no live rollback run. |
| Monitoring and logging | Partially implemented | Health endpoint, probes, and standard logs exist; no metrics/centralized monitoring stack. |
| Blue-green deployment | Implemented but not verified | Manifests and selector-switch helper checked; live traffic switch pending. |
| Canary deployment | Implemented but not verified | Istio configuration and weight helper checked; service mesh execution pending. |
| Shadow deployment | Implemented but not verified | Mirror configuration and write isolation tested locally; live mesh execution pending. |
| A/B testing | Implemented but not verified | Header-routing configuration checked; live mesh execution pending. |
| Documentation and report | Implemented and verified | Setup, limitations, status, and evidence placeholders are documented. |

## Challenges and conclusion

The existing Assignment 1 repository used a browser UI and a different application configuration from the separate Assignment 2 snapshot. The DevOps settings were integrated into the existing app rather than replacing that UI or its business logic. External tooling was unavailable, so this report separates local test evidence from configuration review and pending live-service validation. Before academic submission, run the Jenkins/SonarQube pipeline and Docker/Minikube demonstrations, then replace the labelled screenshot placeholders with genuine evidence.
