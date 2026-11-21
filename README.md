# ACEest Fitness & Gym

ACEest Fitness & Gym is a Flask web application for fitness staff to manage clients, training programs, workouts, memberships, and progress. Assignment 2 adds automated validation, code-quality analysis, container packaging, and Kubernetes deployment configuration while retaining the Assignment 1 application, templates, styles, and workflows.

## Application features

- Staff login with credentials supplied through environment variables
- Dashboard with client, membership, program, and workout summaries
- Client create, view, update, and delete operations
- Fat Loss, Muscle Gain, and Beginner programs with calorie factors 22, 35, and 26
- Rule-based program generation for beginner, intermediate, and advanced levels
- Workout logging and weekly adherence records
- Membership end dates and JSON health endpoint at `/health`

The application factory and SQLite data access are in `app.py`. Browser views are in `templates/`, styles are in `static/`, and tests use temporary databases.

## Project Architecture

```text
Staff browser
    -> Flask application served by Gunicorn
    -> SQLite database on the application data volume

GitHub
    -> GitHub Actions: syntax, lint, tests, container build, health check
    -> Jenkins: tests, coverage, SonarQube Quality Gate, Docker build
    -> Optional Docker Hub publish and Kubernetes deployment
```

The Flask application exposes its health check at `/health`. Kubernetes probes use that endpoint, while the Service routes cluster traffic to the application pods.

## Technology

- Python 3.12, Flask, SQLite, and Gunicorn
- Pytest, pytest-cov, Ruff, and PyYAML
- Docker
- Jenkins and GitHub Actions
- SonarQube
- Kubernetes and Minikube
- PowerShell helper scripts

## Local setup

Run these commands from the repository directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

$env:DEMO_USERNAME = Read-Host "Choose a local administrator username"
$localPassword = Read-Host "Choose a local administrator password" -AsSecureString
$env:DEMO_PASSWORD = [System.Net.NetworkCredential]::new("", $localPassword).Password
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
python app.py
```

Open `http://127.0.0.1:5000/`. Do not commit environment files or credentials. `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `FLASK_SECRET_KEY` are also accepted for container and Kubernetes configuration.

## Tests and coverage

```powershell
python -m compileall -q app.py tests
python -m ruff check app.py tests
python -m pytest -q
python -m pytest -q --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html --cov-report=term-missing
```

On Windows, `.\scripts\run-local-tests.ps1` runs the coverage command. Generated coverage, cache, database, and temporary files are excluded from Git.

## Docker Build Instructions

Build the runtime image:

```powershell
docker build --target runtime --build-arg APP_VERSION=3.2.4 -t aceest-fitness:3.2.4 .
```

Provide credentials from the current shell when running the container:

```powershell
docker run --rm -p 5000:5000 `
  --env DEMO_USERNAME `
  --env DEMO_PASSWORD `
  --env SECRET_KEY `
  aceest-fitness:3.2.4
```

The runtime image runs Gunicorn as a non-root user, stores SQLite data under `/data`, and exposes `/health`. To run the test stage:

```powershell
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

## GitHub Actions

The workflow in `.github/workflows/main.yml` installs development dependencies, compiles and lints the Python code, runs tests, builds the runtime and test images, runs the test image, and checks the runtime health endpoint. It runs on pushes and pull requests.

## CI/CD Pipeline Flow

GitHub Actions runs syntax validation, Ruff, Pytest, and Docker image/container checks. Jenkins runs the ordered pipeline below, including coverage and the SonarQube Quality Gate before building and optionally publishing or deploying the image.

## Jenkins Pipeline Stages

`Jenkinsfile` runs these stages in order:

1. Checkout and select `IMAGE_VERSION` or the repository `VERSION`.
2. Set up Python and install `requirements-dev.txt`.
3. Compile Python and run Ruff.
4. Run Pytest and publish JUnit results.
5. Generate XML/HTML coverage reports.
6. Run SonarQube analysis and wait for the Quality Gate.
7. Build the versioned runtime image and the isolated test image; run the container tests.
8. Optionally authenticate to Docker Hub, tag the image with version and commit SHA, and push both tags.
9. Optionally deploy the pushed image to Kubernetes, roll back on a failed rollout, and verify deployment status and Service.

Configure Jenkins with:

- A Multibranch Pipeline or Pipeline-from-SCM job pointing at this repository and `Jenkinsfile`.
- An agent labelled `linux-docker` with Python 3 (including `venv`/`pip`), Git, Docker CLI with daemon access, `sonar-scanner` on `PATH`, and `kubectl` when deployment is enabled.
- The Jenkins Git, Pipeline/Declarative Pipeline, SonarQube Scanner, Credentials Binding, and JUnit plugins. Docker Pipeline is not used; the Jenkinsfile invokes the Docker CLI.
- A SonarQube server configured with the name `sonarqube`, and a SonarQube webhook to `<JENKINS_URL>/sonarqube-webhook/` for Quality Gate callbacks.
- A Docker Hub **Username with password** credential with ID `dockerhub-creds`.
- A Kubernetes kubeconfig **Secret file** credential with ID `kubeconfig` when deployment is enabled.

Set `IMAGE_REPO` to the Docker Hub namespace/repository to publish. `PUBLISH_IMAGE` and `DEPLOY_TO_K8S` default to false; deployment requires publishing to be enabled. Store credentials in Jenkins or the cluster, not in this repository.

## SonarQube Analysis

The repository's `sonar-project.properties` configures source, test, and coverage locations. Jenkins runs analysis after coverage generation and blocks later stages if the Quality Gate fails. A local scan can be run after generating `coverage.xml`:

```powershell
sonar-scanner -Dproject.settings=sonar-project.properties
```

## Kubernetes Deployment Instructions

The primary rolling deployment uses `k8s/rolling-update.yaml` and the persistent volume claim in `k8s/pvc.yaml`. Create the `aceest-secrets` Kubernetes Secret with keys `admin-username`, `admin-password`, and `flask-secret-key` using your cluster's approved secret-handling process. Do not add Secret manifests or credential values to Git.

Build and load the image into Minikube, then apply the rolling resources:

```powershell
minikube start
docker build --target runtime --build-arg APP_VERSION=3.2.4 -t aceest-fitness:3.2.4 .
minikube image load aceest-fitness:3.2.4
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/rolling-update.yaml
kubectl rollout status deployment/aceest-rolling --timeout=180s
kubectl port-forward service/aceest-rolling-service 18080:80
```

In another terminal, check `http://127.0.0.1:18080/health`. The rolling Service is ClusterIP. `k8s/service.yaml` belongs to the separate blue-green setup and should not be applied for the rolling deployment.

The assignment submission manifests are also available under `kubernetes/`. They define the `aceest-assignment` Deployment and matching ClusterIP Service. After building/loading `aceest-fitness:3.2.4`, creating the `aceest-secrets` Secret, and applying `k8s/pvc.yaml`, apply the assignment manifests:

```powershell
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl rollout status deployment/aceest-assignment --timeout=180s
kubectl port-forward service/aceest-assignment-service 18080:80
```

The existing Jenkins deployment continues to use `k8s/rolling-update.yaml`; the two deployment examples have separate names and selectors.

The sample manifests use non-secure session cookies for local HTTP demonstrations. For a production deployment behind TLS, set `SESSION_COOKIE_SECURE=true` through the deployment configuration.

Update the rolling deployment and roll it back with:

```powershell
kubectl set image deployment/aceest-rolling aceest=aceest-fitness:3.2.5
kubectl set env deployment/aceest-rolling APP_VERSION=3.2.5
kubectl rollout status deployment/aceest-rolling --timeout=180s
kubectl rollout history deployment/aceest-rolling
kubectl rollout undo deployment/aceest-rolling
kubectl rollout status deployment/aceest-rolling --timeout=180s
```

The blue-green, canary, shadow, and A/B resources are separate examples. Canary, shadow, and A/B traffic routing require Istio or a compatible service mesh. Read the notes under `deployment-strategies/` and apply only the resources needed for a specific strategy. PowerShell helpers are in `scripts/`.

## Repository layout

```text
app.py                       Flask application and SQLite access
templates/ and static/       Assignment 1 browser interface
tests/                       Application and Kubernetes manifest tests
k8s/                         Existing deployment strategy manifests
kubernetes/                  Assignment Deployment and Service manifests
deployment-strategies/       Deployment strategy notes
scripts/                     PowerShell deployment and test helpers
report/                      Assignment 2 submission report
reports/                     Existing audit report and CI test outputs
Dockerfile                   Test and non-root runtime image stages
Jenkinsfile                  Jenkins CI/CD pipeline
sonar-project.properties     SonarQube and coverage settings
```

## Assignment Deliverables

- Flask application and automated tests
- GitHub Actions and Jenkins CI/CD configuration
- Docker runtime and test image definitions
- SonarQube project configuration
- Kubernetes rolling Deployment and Service manifests
- Assignment report at `report/Assignment2_Report.md`

## Submission Evidence Placeholders

Replace each placeholder only with evidence captured from the corresponding environment.

- Application endpoint URL: `[Deployment URL: pending deployment]`
- Jenkins pipeline: `[Screenshot placeholder: Jenkins stages and successful build]`
- SonarQube: `[Screenshot placeholder: analysis and Quality Gate]`
- Docker: `[Screenshot placeholder: image build and container health check]`
- Kubernetes: `[Screenshot placeholder: Deployment, Pods, Service, and health check]`

## External validation

Docker, Kubernetes/Minikube, Jenkins, SonarQube, and Docker Hub require their respective local services, agents, credentials, or accounts. Their build, scan, deployment, and publishing results must be captured in those environments; this repository does not claim those external steps ran without evidence.
