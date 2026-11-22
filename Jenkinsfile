pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(name: 'IMAGE_REPO', defaultValue: '', description: 'Docker Hub repository, for example username/aceest-fitness')
        string(name: 'IMAGE_VERSION', defaultValue: '', description: 'Optional image version; defaults to VERSION')
        string(name: 'PYTHON_EXE', defaultValue: '', description: 'Optional absolute path to python.exe on the Windows Jenkins agent')
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
                    env.GIT_SHORT_SHA = bat(
                        script: '@git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Set up Python environment') {
            steps {
                script {
                    env.PYTHON_EXE = powershell(
                        returnStdout: true,
                        script: '''
                            $pythonExe = $env:PYTHON_EXE
                            if (-not $pythonExe) {
                                $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
                                if ($launcher) {
                                    $pythonExe = & $launcher.Source -3 -c 'import sys; print(sys.executable)' | Select-Object -Last 1
                                    if ($LASTEXITCODE -ne 0) {
                                        throw 'The Windows Python launcher could not locate a Python installation.'
                                    }
                                }
                            }
                            if (-not $pythonExe) {
                                throw 'Python was not found. Set the PYTHON_EXE build parameter to the full path of python.exe, or install the Python launcher for the Jenkins service account.'
                            }
                            $pythonExe = $pythonExe.Trim().Trim('"')
                            if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
                                throw "Python executable not found: $pythonExe"
                            }
                            $null = & $pythonExe --version
                            if ($LASTEXITCODE -ne 0) {
                                throw "Python executable failed: $pythonExe"
                            }
                            Write-Output $pythonExe
                        '''
                    ).trim()
                }
                bat '''
                    @echo off
                    "%PYTHON_EXE%" -m venv .venv
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('Install dependencies') {
            steps {
                bat '''
                    @echo off
                    .venv\\Scripts\\python.exe -m pip install --upgrade pip
                    if errorlevel 1 exit /b %errorlevel%
                    .venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('Syntax and lint validation') {
            steps {
                bat '''
                    @echo off
                    .venv\\Scripts\\python.exe -m compileall -q app.py tests
                    if errorlevel 1 exit /b %errorlevel%
                    .venv\\Scripts\\python.exe -m ruff check app.py tests
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('Automated testing using Pytest') {
            steps {
                bat '''
                    @echo off
                    if not exist reports mkdir reports
                    .venv\\Scripts\\python.exe -m pytest -q --junitxml=reports/pytest-results.xml
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('Generate test coverage report') {
            steps {
                bat '''
                    @echo off
                    .venv\\Scripts\\python.exe -m pytest -q --cov=app --cov-report=xml:coverage.xml --cov-report=html:coverage_html --cov-report=term-missing
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('SonarQube analysis') {
            steps {
                script {
                    try {
                        withSonarQubeEnv('sonarqube') {
                            bat '''
                                @echo off
                                sonar-scanner -Dproject.settings=sonar-project.properties
                                if errorlevel 1 exit /b %errorlevel%
                            '''
                        }
                    } catch (NoSuchMethodError error) {
                        if (!error.message?.contains("withSonarQubeEnv")) {
                            throw error
                        }
                        echo 'SonarQube plugin is not installed; skipping SonarQube analysis and quality gate.'
                        env.SONARQUBE_PLUGIN_AVAILABLE = 'false'
                    }
                }
            }
        }

        stage('SonarQube Quality Gate') {
            when {
                expression { env.SONARQUBE_PLUGIN_AVAILABLE != 'false' }
            }
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
                bat '''
                    @echo off
                    docker build --target runtime --build-arg APP_VERSION="%APP_VERSION%" --tag "%LOCAL_IMAGE%" --tag "aceest-fitness:%GIT_SHORT_SHA%" .
                    if errorlevel 1 exit /b %errorlevel%
                '''
            }
        }

        stage('Docker test image') {
            steps {
                bat '''
                    @echo off
                    docker build --target test --tag "aceest-fitness:test-%GIT_SHORT_SHA%" .
                    if errorlevel 1 exit /b %errorlevel%
                    docker run --rm "aceest-fitness:test-%GIT_SHORT_SHA%"
                    if errorlevel 1 exit /b %errorlevel%
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
                    powershell '''
                        $env:DOCKER_PASS | docker login --username $env:DOCKER_USER --password-stdin
                        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
                    '''
                }
            }
        }

        stage('Docker image tagging and publishing') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                bat '''
                    @echo off
                    docker tag "%LOCAL_IMAGE%" "%IMAGE_REPO%:%APP_VERSION%"
                    if errorlevel 1 exit /b %errorlevel%
                    docker tag "%LOCAL_IMAGE%" "%IMAGE_REPO%:%GIT_SHORT_SHA%"
                    if errorlevel 1 exit /b %errorlevel%
                    docker push "%IMAGE_REPO%:%APP_VERSION%"
                    if errorlevel 1 exit /b %errorlevel%
                    docker push "%IMAGE_REPO%:%GIT_SHORT_SHA%"
                    if errorlevel 1 exit /b %errorlevel%
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
                    powershell '''
                        $ErrorActionPreference = 'Stop'
                        $deploymentStarted = $false

                        function Invoke-Kubectl {
                            & kubectl @args
                            if ($LASTEXITCODE -ne 0) {
                                throw "kubectl $($args -join ' ') failed with exit code $LASTEXITCODE"
                            }
                        }

                        try {
                            Invoke-Kubectl apply -f k8s/pvc.yaml
                            Invoke-Kubectl apply -f k8s/rolling-update.yaml
                            $deploymentStarted = $true
                            Invoke-Kubectl set image deployment/aceest-rolling "aceest=$($env:IMAGE_REPO):$($env:APP_VERSION)"
                            Invoke-Kubectl set env deployment/aceest-rolling "APP_VERSION=$($env:APP_VERSION)"
                            Invoke-Kubectl rollout status deployment/aceest-rolling --timeout=180s
                        } catch {
                            if ($deploymentStarted) {
                                Write-Warning 'Deployment failed; attempting rollback.'
                                & kubectl rollout undo deployment/aceest-rolling
                                if ($LASTEXITCODE -ne 0) {
                                    Write-Warning 'Rollback command failed.'
                                }
                                & kubectl rollout status deployment/aceest-rolling --timeout=180s
                                if ($LASTEXITCODE -ne 0) {
                                    Write-Warning 'Deployment did not recover after rollback.'
                                }
                            }
                            throw
                        }
                    '''
                }
            }
        }

        stage('Deployment verification') {
            when { expression { params.DEPLOY_TO_K8S } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    bat '''
                        @echo off
                        kubectl get pods
                        if errorlevel 1 exit /b %errorlevel%
                        kubectl rollout status deployment/aceest-rolling --timeout=180s
                        if errorlevel 1 exit /b %errorlevel%
                        kubectl get service aceest-rolling-service
                        if errorlevel 1 exit /b %errorlevel%
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
