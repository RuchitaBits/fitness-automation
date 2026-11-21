pipeline {
    agent { label 'linux-docker' }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(name: 'IMAGE_REPO', defaultValue: '', description: 'Docker Hub repository, for example username/aceest-fitness')
        string(name: 'IMAGE_VERSION', defaultValue: '', description: 'Optional image version; defaults to VERSION')
        booleanParam(name: 'PUBLISH_IMAGE', defaultValue: false, description: 'Push the verified image')
        booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy after publishing')
    }

    environment {
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = params.IMAGE_VERSION.trim()
                        ? params.IMAGE_VERSION.trim()
                        : readFile('VERSION').trim()
                    env.GIT_SHORT_SHA = sh(script: 'git rev-parse --short=12 HEAD', returnStdout: true).trim()
                }
            }
        }

        stage('Set up Python environment') {
            steps {
                sh 'python3 -m venv .venv'
            }
        }

        stage('Install dependencies') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/python -m pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Syntax and lint validation') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m compileall -q app.py tests
                    .venv/bin/python -m ruff check app.py tests
                '''
            }
        }

        stage('Automated testing using Pytest') {
            steps {
                sh '''
                    set -eu
                    mkdir -p reports
                    .venv/bin/python -m pytest -q --junitxml=reports/pytest-results.xml
                '''
            }
        }

        stage('Generate test coverage report') {
            steps {
                sh '''
                    set -eu
                    .venv/bin/python -m pytest -q --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=html:coverage_html \
                        --cov-report=term-missing
                '''
            }
        }

        stage('SonarQube analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh 'sonar-scanner -Dproject.settings=sonar-project.properties'
                }
            }
        }

        stage('SonarQube Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Docker image build') {
            steps {
                script {
                    env.LOCAL_IMAGE = "aceest-fitness:${env.APP_VERSION}"
                }
                sh '''
                    set -eu
                    docker build --target runtime --build-arg APP_VERSION="$APP_VERSION" \
                        --tag "$LOCAL_IMAGE" --tag "aceest-fitness:$GIT_SHORT_SHA" .
                '''
            }
        }

        stage('Docker test image') {
            steps {
                sh '''
                    set -eu
                    docker build --target test --tag "aceest-fitness:test-$GIT_SHORT_SHA" .
                    docker run --rm "aceest-fitness:test-$GIT_SHORT_SHA"
                '''
            }
        }

        stage('Docker Hub authentication') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                script {
                    env.IMAGE_REPO = params.IMAGE_REPO.trim()
                    if (!env.IMAGE_REPO) {
                        error('Set IMAGE_REPO to username/aceest-fitness before publishing.')
                    }
                }
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh 'set +x; printf "%s" "$DOCKER_PASS" | docker login --username "$DOCKER_USER" --password-stdin'
                }
            }
        }

        stage('Docker image tagging and publishing') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                sh '''
                    set -eu
                    docker tag "$LOCAL_IMAGE" "$IMAGE_REPO:$APP_VERSION"
                    docker tag "$LOCAL_IMAGE" "$IMAGE_REPO:$GIT_SHORT_SHA"
                    docker push "$IMAGE_REPO:$APP_VERSION"
                    docker push "$IMAGE_REPO:$GIT_SHORT_SHA"
                '''
            }
        }

        stage('Kubernetes deployment') {
            when { expression { params.DEPLOY_TO_K8S } }
            steps {
                script {
                    if (!params.PUBLISH_IMAGE) {
                        error('DEPLOY_TO_K8S requires PUBLISH_IMAGE.')
                    }
                }
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        set -eu
                        DEPLOY_STARTED=0
                        rollback_on_failure() {
                            status=$?
                            if [ "$status" -ne 0 ] && [ "$DEPLOY_STARTED" -eq 1 ]; then
                                kubectl rollout undo deployment/aceest-rolling || true
                                kubectl rollout status deployment/aceest-rolling --timeout=180s || true
                            fi
                            exit "$status"
                        }
                        trap rollback_on_failure EXIT
                        kubectl apply -f k8s/pvc.yaml
                        kubectl apply -f k8s/rolling-update.yaml
                        DEPLOY_STARTED=1
                        kubectl set image deployment/aceest-rolling aceest="$IMAGE_REPO:$APP_VERSION"
                        kubectl set env deployment/aceest-rolling APP_VERSION="$APP_VERSION"
                        kubectl rollout status deployment/aceest-rolling --timeout=180s
                    '''
                }
            }
        }

        stage('Deployment verification') {
            when { expression { params.DEPLOY_TO_K8S } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        set -eu
                        kubectl get pods
                        kubectl rollout status deployment/aceest-rolling --timeout=180s
                        kubectl get service aceest-rolling-service
                    '''
                }
            }
        }
    }

    post {
        always {
            junit testResults: 'reports/pytest-results.xml', allowEmptyResults: true
            archiveArtifacts(
                artifacts: 'coverage.xml,coverage_html/**,reports/pytest-results.xml',
                allowEmptyArchive: true
            )
        }
    }
}
