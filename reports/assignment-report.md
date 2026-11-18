# ACEest Fitness & Gym - DevOps Assignment 2 Report

## Objective

Extend the Assignment 1 fitness-management application with repeatable testing, code-quality analysis, container packaging, and deployment configuration while retaining the existing Flask application, browser interface, and business workflows.

## Application and architecture

The Flask web application continues to support staff login, client management, training programs, workouts, memberships, and progress tracking. SQLite remains the persistence layer. Application templates and styles are retained.

```text
GitHub
  -> GitHub Actions and Jenkins
  -> Pytest, coverage, Ruff, and SonarQube
  -> Docker runtime image
  -> Optional Docker Hub publishing
  -> Kubernetes deployment and rollout verification
```

The rolling deployment uses a persistent volume claim. Blue-green resources are separate; canary, shadow, and A/B traffic behavior requires Istio or a compatible service mesh.

## DevOps implementation

- Pytest and pytest-cov run application and manifest tests and generate local coverage reports.
- Ruff and Python compilation run in GitHub Actions and Jenkins.
- SonarQube reads `sonar-project.properties` and the generated `coverage.xml`.
- The multi-stage Dockerfile separates the test image from the non-root runtime image.
- Jenkins publishing and deployment are opt-in and use Jenkins credentials.
- Kubernetes manifests define health probes, resource requests and limits, secrets, persistent storage, and a rolling update strategy.
- PowerShell scripts support local deployment, blue-green switching, canary weights, rollback, and tests.

## Verification record

On Windows with Python 3.14.8, the merged test suite completed with **21 passed** and **90% application coverage**. Python compilation, Ruff checks, Kubernetes YAML parsing and selector checks, and PowerShell syntax parsing passed. The repository CI target remains Python 3.12; that runtime was not available for local verification.

Docker, `kubectl`, Minikube, Jenkins, and SonarQube were unavailable in the local environment. Docker image build/health, SonarQube analysis, Jenkins execution, Kubernetes deployment/rollout/rollback, and Docker Hub publishing therefore remain unverified. No results for those external steps are claimed.

## Manual setup and evidence

Before a live demonstration, configure Jenkins and SonarQube, add Docker Hub and kubeconfig credentials if those stages are required, create the Kubernetes Secret through the approved cluster process, and deploy to a prepared cluster. Record actual test, scan, image, rollout, and rollback output from those runs. No screenshots or service results are included unless they were actually captured.
