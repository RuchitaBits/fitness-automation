pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        string(name: 'IMAGE_REPO', defaultValue: 'ruchitabits/aceest-fitness', description: 'Docker Hub repository, for example username/aceest-fitness')
        string(name: 'IMAGE_VERSION', defaultValue: 'v1', description: 'Optional image version')
        string(name: 'PYTHON_EXE', defaultValue: 'C:\\Users\\ruchi\\AppData\\Local\\Programs\\Python\\Python314\\python.exe', description: 'Absolute path to python.exe on the Windows Jenkins agent')
        string(name: 'DOCKER_EXE', defaultValue: 'C:\\Users\\ruchi\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe', description: 'Docker executable path on Windows; Linux agents use docker from PATH by default')
        booleanParam(name: 'PUBLISH_IMAGE', defaultValue: false, description: 'Push the verified image')
        booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy after publishing')
    }

    environment {
        PYTHONUNBUFFERED = '1'
        IMAGE_REPO = 'ruchitabits/aceest-fitness'
        IMAGE_VERSION = 'v1'
        PYTHON_EXE = 'C:\\Users\\ruchi\\AppData\\Local\\Programs\\Python\\Python314\\python.exe'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_REPO = params.IMAGE_REPO?.trim() ?: env.IMAGE_REPO
                    env.IMAGE_VERSION = params.IMAGE_VERSION?.trim() ?: env.IMAGE_VERSION
                    env.APP_VERSION = env.IMAGE_VERSION?.trim()
                        ? env.IMAGE_VERSION.trim()
                        : readFile('VERSION').trim()
                    env.GIT_SHORT_SHA = bat(
                        script: '@git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                    def defaultDockerExe = 'C:\\Users\\ruchi\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.exe'
                    def dockerExe = params.DOCKER_EXE?.trim()
                    if (isUnix() && (!dockerExe || dockerExe.equalsIgnoreCase(defaultDockerExe))) {
                        dockerExe = 'docker'
                    }
                    if (!dockerExe) {
                        error('Set DOCKER_EXE to the Docker executable path.')
                    }
                    env.DOCKER_EXE = dockerExe
                    if (!isUnix()) {
                        env.DOCKER_HOST = 'npipe:////./pipe/dockerDesktopLinuxEngine'
                    }
                }
            }
        }

        stage('Set up Python environment') {
            steps {
                script {
                    if (params.PYTHON_EXE?.trim()) {
                        env.PYTHON_EXE = params.PYTHON_EXE.trim()
                    }
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
                    env.LOCAL_IMAGE = "aceest-fitness:${env.IMAGE_VERSION}"
                    if (isUnix()) {
                        sh '''
                            set -eu
                            "$DOCKER_EXE" build --target runtime --build-arg "APP_VERSION=$IMAGE_VERSION" \
                                --tag "$LOCAL_IMAGE" --tag "aceest-fitness:$GIT_SHORT_SHA" .
                        '''
                    } else {
                        bat '''
                            @echo off
                            "%DOCKER_EXE%" build --target runtime --build-arg APP_VERSION="%IMAGE_VERSION%" --tag "%LOCAL_IMAGE%" --tag "aceest-fitness:%GIT_SHORT_SHA%" .
                            if errorlevel 1 exit /b %errorlevel%
                        '''
                    }
                }
            }
        }

        stage('Docker test image') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            set -eu
                            "$DOCKER_EXE" build --target test --tag "aceest-fitness:test-$GIT_SHORT_SHA" .
                            "$DOCKER_EXE" run --rm "aceest-fitness:test-$GIT_SHORT_SHA"
                        '''
                    } else {
                        bat '''
                            @echo off
                            "%DOCKER_EXE%" build --target test --tag "aceest-fitness:test-%GIT_SHORT_SHA%" .
                            if errorlevel 1 exit /b %errorlevel%
                            "%DOCKER_EXE%" run --rm "aceest-fitness:test-%GIT_SHORT_SHA%"
                            if errorlevel 1 exit /b %errorlevel%
                        '''
                    }
                }
            }
        }

        stage('Docker Hub authentication') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                script {
                    if (!env.IMAGE_REPO?.trim()) {
                        error('Set IMAGE_REPO to username/aceest-fitness before publishing.')
                    }
                }
                script {
                    if (!isUnix()) {
                        powershell '''
                            $dockerConfig = $env:DOCKER_CONFIG
                            if ([string]::IsNullOrWhiteSpace($dockerConfig)) {
                                $dockerConfig = 'not set'
                            }

                            Write-Output "Windows identity: $(whoami)"
                            Write-Output "USERPROFILE: $env:USERPROFILE"
                            Write-Output "DOCKER_CONFIG: $dockerConfig"
                            Write-Output "Docker executable: $env:DOCKER_EXE"

                            $dockerContext = & $env:DOCKER_EXE context show
                            Write-Output "Docker context: $dockerContext"

                            $dockerServerName = & $env:DOCKER_EXE info --format '{{.Name}}'
                            Write-Output "Docker server name: $dockerServerName"

                            $dockerClientVersion = & $env:DOCKER_EXE version --format '{{.Client.Version}}'
                            $dockerServerVersion = & $env:DOCKER_EXE version --format '{{.Server.Version}}'
                            Write-Output "Docker client version: $dockerClientVersion"
                            Write-Output "Docker server version: $dockerServerVersion"
                        '''
                    }
                }
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-pat-new',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                set -eu
                                printf "%s" "$DOCKER_PASS" | "$DOCKER_EXE" login --username "$DOCKER_USER" --password-stdin
                            '''
                        } else {
                            powershell '''
                                $dockerUser = $env:DOCKER_USER.Trim()
                                $dockerPassword = $env:DOCKER_PASS
                                $trimmedDockerPassword = ''
                                if ($null -ne $dockerPassword) {
                                    $trimmedDockerPassword = $dockerPassword.Trim()
                                }
                                $passwordPresent = 'false'
                                if (-not [string]::IsNullOrWhiteSpace($dockerPassword)) {
                                    $passwordPresent = 'true'
                                }
                                $passwordBytes = [Text.Encoding]::UTF8.GetBytes($trimmedDockerPassword)
                                $sha256 = [Security.Cryptography.SHA256]::Create()
                                try {
                                    $passwordFingerprint = ([BitConverter]::ToString($sha256.ComputeHash($passwordBytes))).Replace("-", "").Substring(0, 16)
                                } finally {
                                    $sha256.Dispose()
                                    [Array]::Clear($passwordBytes, 0, $passwordBytes.Length)
                                }

                                Write-Output "DOCKER_USER: $env:DOCKER_USER"
                                Write-Output "DOCKER_PASS present: $passwordPresent"
                                Write-Output "DOCKER_PASS trimmed length: $($trimmedDockerPassword.Length)"
                                Write-Output "DOCKER_PASS SHA-256 fingerprint (first 16 hex): $passwordFingerprint"

                                if ([string]::IsNullOrWhiteSpace($dockerUser) -or [string]::IsNullOrWhiteSpace($dockerPassword)) {
                                    throw "Docker Hub credentials are empty."
                                }

                                $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
                                $processStartInfo.FileName = $env:DOCKER_EXE
                                $processStartInfo.Arguments = 'login --username "{0}" --password-stdin' -f $dockerUser
                                $processStartInfo.UseShellExecute = $false
                                $processStartInfo.RedirectStandardInput = $true
                                $processStartInfo.CreateNoWindow = $true

                                $dockerProcess = New-Object System.Diagnostics.Process
                                $dockerStarted = $false
                                try {
                                    $dockerProcess.StartInfo = $processStartInfo
                                    if (-not $dockerProcess.Start()) {
                                        throw "Unable to start Docker Hub authentication."
                                    }
                                    $dockerStarted = $true
                                    $dockerProcess.StandardInput.WriteLine($dockerPassword)
                                    $dockerPassword = $null
                                    $dockerProcess.StandardInput.Close()
                                    $dockerProcess.WaitForExit()
                                    if ($dockerProcess.ExitCode -ne 0) {
                                        throw "Docker Hub authentication failed with exit code $($dockerProcess.ExitCode)."
                                    }
                                } finally {
                                    if ($dockerStarted -and -not $dockerProcess.HasExited) {
                                        $dockerProcess.Kill()
                                        $dockerProcess.WaitForExit()
                                    }
                                    $dockerProcess.Dispose()
                                }
                            '''
                        }
                    }
                }
            }
        }

        stage('Docker image tagging and publishing') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            set -eu
                            "$DOCKER_EXE" tag "$LOCAL_IMAGE" "$IMAGE_REPO:$IMAGE_VERSION"
                            "$DOCKER_EXE" tag "$LOCAL_IMAGE" "$IMAGE_REPO:$GIT_SHORT_SHA"
                            "$DOCKER_EXE" push "$IMAGE_REPO:$IMAGE_VERSION"
                            "$DOCKER_EXE" push "$IMAGE_REPO:$GIT_SHORT_SHA"
                        '''
                    } else {
                        bat '''
                            @echo off
                            "%DOCKER_EXE%" tag "%LOCAL_IMAGE%" "%IMAGE_REPO%:%IMAGE_VERSION%"
                            if errorlevel 1 exit /b %errorlevel%
                            "%DOCKER_EXE%" tag "%LOCAL_IMAGE%" "%IMAGE_REPO%:%GIT_SHORT_SHA%"
                            if errorlevel 1 exit /b %errorlevel%
                            "%DOCKER_EXE%" push "%IMAGE_REPO%:%IMAGE_VERSION%"
                            if errorlevel 1 exit /b %errorlevel%
                            "%DOCKER_EXE%" push "%IMAGE_REPO%:%GIT_SHORT_SHA%"
                            if errorlevel 1 exit /b %errorlevel%
                        '''
                    }
                }
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
