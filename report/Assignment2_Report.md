# DevOps Assignment 2 Report

## 1. Project Overview

ACEest Fitness & Gym is a Flask application for fitness staff to manage clients, training programs, workouts, memberships, and progress. Assignment 2 adds CI/CD, automated quality checks, container packaging, SonarQube configuration, and Kubernetes deployment resources while preserving the existing application behavior.

## 2. Architecture

The browser UI is served by Flask through Gunicorn. Application records are stored in SQLite on the configured data volume. The `/health` endpoint is used by container and Kubernetes health checks.

```text
Browser -> Flask/Gunicorn -> SQLite data volume
GitHub -> GitHub Actions / Jenkins -> tests and quality checks
Jenkins -> Docker image -> optional Docker Hub publish
Docker image -> Kubernetes Deployment -> ClusterIP Service
```

## 3. CI/CD Workflow

GitHub Actions checks out the source, installs development requirements, validates Python syntax and Ruff, runs Pytest, builds runtime and test images, executes container tests, and checks the runtime health endpoint. Jenkins adds coverage generation and SonarQube analysis with a Quality Gate before image build, optional publishing, and optional deployment.

## 4. Jenkins Pipeline

The Jenkins pipeline runs checkout, Python environment setup, dependency installation, syntax/lint validation, Pytest, coverage generation, SonarQube analysis, Quality Gate validation, Docker runtime and test image builds, and container tests. Docker Hub publishing and Kubernetes deployment are opt-in parameters. Publishing uses Jenkins credential `dockerhub-creds`; deployment uses the `kubeconfig` secret-file credential and verifies rollout status. A failed deployment rollout triggers a rollback attempt.

The `linux-docker` agent requires Python 3 with `venv` and `pip`, Git, Docker CLI and daemon access, `sonar-scanner`, and `kubectl` when deployment is enabled. Jenkins must have the Git, Pipeline, SonarQube Scanner, Credentials Binding, and JUnit plugins. Configure the SonarQube server name as `sonarqube` and its webhook to `<JENKINS_URL>/sonarqube-webhook/`.

Jenkins server execution and credentials were not available for verification in the local environment.

## 5. Docker Implementation

The multi-stage Dockerfile defines a test image and a non-root runtime image. The runtime exposes port 5000, stores SQLite data under `/data`, and checks `/health`. Build the images with:

```powershell
docker build --target runtime --build-arg APP_VERSION=3.2.4 -t aceest-fitness:3.2.4 .
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

Docker CLI/daemon availability must be confirmed before claiming local image-build or container-test results.

## 6. Kubernetes Deployment

`kubernetes/deployment.yaml` defines a Flask Deployment with a RollingUpdate strategy, resource limits, health probes, non-root security context, persistent data volume, and secret references for credentials. `kubernetes/service.yaml` exposes the pods through a ClusterIP Service. Apply the existing PVC and create the `aceest-secrets` Secret out of band before deploying:

```powershell
kubectl apply -f k8s/pvc.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl rollout status deployment/aceest-assignment --timeout=180s
```

The Jenkins pipeline retains its existing `k8s/rolling-update.yaml` deployment configuration. Live cluster behavior requires Minikube or another configured Kubernetes cluster and was not verified locally.

## 7. SonarQube Quality Analysis

`sonar-project.properties` configures the project key, source and test paths, Python version, and coverage XML location. Jenkins generates coverage before scanning and waits for the configured Quality Gate. A scan result or quality score is not claimed unless a SonarQube server and scanner have actually run.

## 8. Challenges Faced

The pipeline depends on external Jenkins plugins, credentials, Docker daemon access, SonarQube configuration, and Kubernetes cluster resources. These dependencies require local or hosted infrastructure. Secret values must be supplied through the approved Jenkins/Kubernetes credential mechanisms and must not be committed.

## 9. Results

Python compilation and Ruff checks passed. The new Kubernetes YAML and GitHub Actions workflow structure checks passed. The pytest run could not complete because the selected Python 3.14 interpreter was blocked from loading its SQLite DLL by the local application-control policy; no test or coverage result is claimed for this run.

Docker was unavailable, so image builds and container health checks were not run. Jenkins, SonarQube, Docker Hub, and a Kubernetes cluster were also unavailable for external execution. Record those results only after running the pipeline and deployment in the corresponding environments.

### Evidence placeholders

- Application endpoint URL: `[Deployment URL: pending deployment]`
- Jenkins pipeline: `[Screenshot placeholder: stages and build result]`
- SonarQube: `[Screenshot placeholder: analysis and Quality Gate]`
- Docker: `[Screenshot placeholder: image and health check]`
- Kubernetes: `[Screenshot placeholder: Deployment, Pods, Service, and application health]`

## 10. Conclusion

Assignment 2 extends the existing Flask application with documented, testable DevOps configurations while retaining the prior application and CI implementations. Local automated checks provide reproducible evidence; screenshots and results for Jenkins, SonarQube, Docker publishing, and Kubernetes must be captured from real executions before final submission.
