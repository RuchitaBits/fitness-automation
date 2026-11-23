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
        string(name: 'DOCKER_USER', defaultValue: 'ruchitabits', description: 'Docker Hub username')
        booleanParam(name: 'PUBLISH_IMAGE', defaultValue: false, description: 'Push the verified image')
        booleanParam(name: 'DEPLOY_TO_K8S', defaultValue: false, description: 'Deploy after publishing')
        booleanParam(name: 'DOCKER_AUTH_DIAGNOSTIC', defaultValue: false, description: 'Test Docker Hub authentication only; skip publishing and deployment')
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
                    def dockerUser = params.DOCKER_USER?.trim()
                    if (dockerUser && env.IMAGE_REPO == 'ruchitabits/aceest-fitness') {
                        env.IMAGE_REPO = "${dockerUser}/aceest-fitness"
                    }
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
                        env.DOCKER_CONTEXT = ''
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
                        powershell '''
                            $dockerServerVersion = & $env:DOCKER_EXE info --format '{{.ServerVersion}}' 2>$null
                            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($dockerServerVersion)) {
                                throw "Cannot connect to Docker Engine at npipe:////./pipe/dockerDesktopLinuxEngine. Ensure Docker Desktop's Linux engine is running and the Jenkins service account can access the named pipe."
                            }
                        '''
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

        stage('Docker Hub authentication diagnostic') {
            when { expression { params.DOCKER_AUTH_DIAGNOSTIC } }
            steps {
                withCredentials([string(credentialsId: 'dockerhub-pat-working', variable: 'DOCKER_PAT')]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                set +x
                                set -eu
                                dockerExe="${DOCKER_EXE:-docker}"
                                dockerUser="${DOCKER_USER:-}"
                                dockerPat="${DOCKER_PAT:-}"
                                previousDockerConfig="${DOCKER_CONFIG-}"
                                hadDockerConfig="${DOCKER_CONFIG+x}"
                                tempDockerConfig=''
                                loginStatus=1

                                cleanup() {
                                    unset DOCKER_PAT dockerPat
                                    if [ "$hadDockerConfig" = "x" ]; then
                                        DOCKER_CONFIG="$previousDockerConfig"
                                        export DOCKER_CONFIG
                                    else
                                        unset DOCKER_CONFIG
                                    fi
                                    if [ -n "$tempDockerConfig" ]; then
                                        rm -rf -- "$tempDockerConfig" >/dev/null 2>&1 || true
                                    fi
                                }
                                trap cleanup EXIT

                                if [ -n "$dockerUser" ] && [ -n "$dockerPat" ]; then
                                    tempDockerConfig=$(mktemp -d 2>/dev/null || true)
                                    if [ -n "$tempDockerConfig" ]; then
                                        DOCKER_CONFIG="$tempDockerConfig"
                                        export DOCKER_CONFIG
                                        unset DOCKER_PAT
                                        set +e
                                        printf "%s\n" "$dockerPat" | "$dockerExe" login --username "$dockerUser" --password-stdin >/dev/null 2>&1
                                        loginStatus=$?
                                        set -e
                                    fi
                                fi
                                unset dockerPat

                                if [ "$loginStatus" -eq 0 ]; then
                                    printf 'Docker Hub authentication succeeded (exit code: %s)\n' "$loginStatus"
                                else
                                    printf 'Docker Hub authentication failed (exit code: %s)\n' "$loginStatus"
                                fi
                                exit "$loginStatus"
                            '''
                        } else {
                            powershell '''
                                $dockerUser = [string]$env:DOCKER_USER
                                $dockerPat = [string]$env:DOCKER_PAT
                                $previousDockerConfig = $env:DOCKER_CONFIG
                                $hadDockerConfig = Test-Path Env:DOCKER_CONFIG
                                $tempDockerConfig = $null
                                $dockerProcess = $null
                                $dockerStarted = $false
                                $stdoutTask = $null
                                $stderrTask = $null
                                $dockerStdout = ''
                                $dockerStderr = ''
                                $exceptionMessage = ''
                                $patBytes = $null
                                $hashBytes = $null
                                $sha256 = $null
                                $fingerprint = $null
                                $authenticationSucceeded = $false
                                $cleanupSucceeded = $true
                                $exitCode = 1

                                try {
                                    if ([string]::IsNullOrWhiteSpace($dockerUser) -or
                                        [string]::IsNullOrWhiteSpace($dockerPat)) {
                                        throw 'Docker Hub authentication inputs are empty.'
                                    }

                                    $patBytes = [Text.Encoding]::UTF8.GetBytes($dockerPat)
                                    try {
                                        $sha256 = [Security.Cryptography.SHA256]::Create()
                                        $hashBytes = $sha256.ComputeHash($patBytes)
                                        $fingerprint = ([BitConverter]::ToString($hashBytes, 0, 6)).Replace('-', '')
                                        Write-Output "Jenkins credential fingerprint: $fingerprint"
                                    } finally {
                                        if ($null -ne $patBytes) {
                                            [Array]::Clear($patBytes, 0, $patBytes.Length)
                                        }
                                        if ($null -ne $hashBytes) {
                                            [Array]::Clear($hashBytes, 0, $hashBytes.Length)
                                        }
                                        if ($null -ne $sha256) {
                                            $sha256.Dispose()
                                        }
                                        $patBytes = $null
                                        $hashBytes = $null
                                        $sha256 = $null
                                        $fingerprint = $null
                                    }

                                    $dockerUser = $dockerUser.Trim()
                                    $dockerPat = $dockerPat.Trim()
                                    $tempDockerConfig = Join-Path ([System.IO.Path]::GetTempPath()) (
                                        'docker-auth-diagnostic-' + [Guid]::NewGuid().ToString('N')
                                    )
                                    [System.IO.Directory]::CreateDirectory($tempDockerConfig) | Out-Null
                                    $env:DOCKER_CONFIG = $tempDockerConfig
                                    Remove-Item Env:DOCKER_PAT -ErrorAction SilentlyContinue

                                    $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
                                    $processStartInfo.FileName = $env:DOCKER_EXE
                                    $processStartInfo.Arguments = 'login --username "{0}" --password-stdin' -f $dockerUser
                                    $processStartInfo.UseShellExecute = $false
                                    $processStartInfo.RedirectStandardInput = $true
                                    $processStartInfo.RedirectStandardOutput = $true
                                    $processStartInfo.RedirectStandardError = $true
                                    $processStartInfo.CreateNoWindow = $true

                                    $dockerProcess = New-Object System.Diagnostics.Process
                                    $dockerProcess.StartInfo = $processStartInfo
                                    if (-not $dockerProcess.Start()) {
                                        throw 'Docker Hub authentication process did not start.'
                                    }
                                    $dockerStarted = $true
                                    $stdoutTask = $dockerProcess.StandardOutput.ReadToEndAsync()
                                    $stderrTask = $dockerProcess.StandardError.ReadToEndAsync()

                                    try {
                                        $dockerProcess.StandardInput.WriteLine($dockerPat)
                                        $dockerProcess.StandardInput.Flush()
                                    } finally {
                                        $dockerProcess.StandardInput.Close()
                                    }

                                    $dockerProcess.WaitForExit()
                                    $dockerStdout = [string]$stdoutTask.GetAwaiter().GetResult()
                                    $dockerStderr = [string]$stderrTask.GetAwaiter().GetResult()
                                    if (-not [string]::IsNullOrEmpty($dockerPat)) {
                                        $dockerStdout = $dockerStdout.Replace($dockerPat, '[REDACTED]')
                                        $dockerStderr = $dockerStderr.Replace($dockerPat, '[REDACTED]')
                                    }
                                    $exitCode = $dockerProcess.ExitCode
                                    $authenticationSucceeded = ($exitCode -eq 0)
                                } catch {
                                    $authenticationSucceeded = $false
                                    $exceptionMessage = [string]$_.Exception.Message
                                    if (-not [string]::IsNullOrEmpty($dockerPat)) {
                                        $exceptionMessage = $exceptionMessage.Replace($dockerPat, '[REDACTED]')
                                    }
                                    if ($dockerStarted -and $dockerProcess.HasExited) {
                                        $exitCode = $dockerProcess.ExitCode
                                    } else {
                                        $exitCode = 1
                                    }
                                } finally {
                                    $dockerPat = $null
                                    Remove-Item Env:DOCKER_PAT -ErrorAction SilentlyContinue

                                    if ($dockerStarted -and -not $dockerProcess.HasExited) {
                                        try {
                                            $dockerProcess.StandardInput.Close()
                                        } catch {
                                            $cleanupSucceeded = $false
                                        }
                                        try {
                                            $dockerProcess.Kill()
                                            $dockerProcess.WaitForExit()
                                        } catch {
                                            $cleanupSucceeded = $false
                                            $exitCode = 1
                                        }
                                    }
                                    if ($null -ne $dockerProcess) {
                                        if ($dockerStarted -and $dockerProcess.HasExited) {
                                            if ($null -ne $stdoutTask) {
                                                try {
                                                    $null = $stdoutTask.GetAwaiter().GetResult()
                                                } catch {
                                                    $cleanupSucceeded = $false
                                                }
                                            }
                                            if ($null -ne $stderrTask) {
                                                try {
                                                    $null = $stderrTask.GetAwaiter().GetResult()
                                                } catch {
                                                    $cleanupSucceeded = $false
                                                }
                                            }
                                        }
                                        try {
                                            $dockerProcess.Dispose()
                                        } catch {
                                            $cleanupSucceeded = $false
                                        }
                                    }

                                    if ($hadDockerConfig) {
                                        $env:DOCKER_CONFIG = $previousDockerConfig
                                    } else {
                                        Remove-Item Env:DOCKER_CONFIG -ErrorAction SilentlyContinue
                                    }
                                    if ($null -ne $tempDockerConfig -and
                                        (Test-Path -LiteralPath $tempDockerConfig)) {
                                        try {
                                            Remove-Item -LiteralPath $tempDockerConfig -Recurse -Force -ErrorAction Stop
                                        } catch {
                                            $cleanupSucceeded = $false
                                            $exitCode = 1
                                        }
                                    }
                                }

                                if (-not $cleanupSucceeded) {
                                    $authenticationSucceeded = $false
                                }
                                if (-not $authenticationSucceeded -and $exitCode -eq 0) {
                                    $exitCode = 1
                                }
                                $diagnosticText = "$dockerStdout`n$dockerStderr`n$exceptionMessage"
                                if ($authenticationSucceeded) {
                                    $diagnosticCategory = 'Docker Hub authentication succeeded.'
                                } elseif (-not $cleanupSucceeded) {
                                    $diagnosticCategory = 'Docker authentication process failed.'
                                } elseif ($diagnosticText -match '(?i)(unauthorized|incorrect username or password|authentication required|denied: requested access)') {
                                    $diagnosticCategory = 'Docker Hub rejected the credentials (unauthorized).'
                                } elseif ($diagnosticText -match '(?i)(no such host|connection refused|connection reset|network is unreachable|no route to host|timed out|timeout|deadline exceeded|TLS handshake|unable to connect|could not connect|cannot connect|dial tcp|proxyconnect|error during connect|cannot connect to the docker daemon|pipe.*(not found|does not exist|cannot find)|system cannot find the file specified)') {
                                    $diagnosticCategory = 'Docker Hub connection failed.'
                                } else {
                                    $diagnosticCategory = 'Docker authentication process failed.'
                                }
                                $dockerStdout = $null
                                $dockerStderr = $null
                                $exceptionMessage = $null
                                $diagnosticText = $null
                                $dockerPat = $null
                                Write-Output $diagnosticCategory
                                if (-not $authenticationSucceeded) {
                                    exit $exitCode
                                }
                            '''
                        }
                    }
                }
            }
        }

        stage('Docker Hub authentication') {
            when { expression { params.PUBLISH_IMAGE && !params.DOCKER_AUTH_DIAGNOSTIC } }
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
                            Write-Output "Docker endpoint: $env:DOCKER_HOST"

                            $dockerServerName = & $env:DOCKER_EXE info --format '{{.Name}}'
                            Write-Output "Docker server name: $dockerServerName"

                            $dockerClientVersion = & $env:DOCKER_EXE version --format '{{.Client.Version}}'
                            $dockerServerVersion = & $env:DOCKER_EXE version --format '{{.Server.Version}}'
                            Write-Output "Docker client version: $dockerClientVersion"
                            Write-Output "Docker server version: $dockerServerVersion"
                        '''
                    }
                }
                withCredentials([string(credentialsId: 'dockerhub-pat-working', variable: 'DOCKER_PAT')]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                set +x
                                set -eu
                                dockerPat="${DOCKER_PAT:-}"
                                trap 'unset dockerPat DOCKER_PAT' EXIT
                                if [ -z "${DOCKER_USER:-}" ]; then
                                    echo "Set the DOCKER_USER build parameter before publishing." >&2
                                    exit 1
                                fi
                                if [ -z "$dockerPat" ]; then
                                    echo "Set the DOCKER_PAT build parameter before publishing." >&2
                                    exit 1
                                fi
                                unset DOCKER_PAT
                                set +e
                                printf "%s" "$dockerPat" | "$DOCKER_EXE" login --username "$DOCKER_USER" --password-stdin
                                login_status=$?
                                set -e
                                unset dockerPat
                                exit "$login_status"
                            '''
                        } else {
                            powershell '''
                                $dockerUser = [string]$env:DOCKER_USER
                                $dockerPat = [string]$env:DOCKER_PAT
                                $dockerProcess = $null
                                $dockerStarted = $false

                                try {
                                    if ([string]::IsNullOrWhiteSpace($dockerUser)) {
                                        throw "Set the DOCKER_USER build parameter before publishing."
                                    }
                                    if ([string]::IsNullOrWhiteSpace($dockerPat)) {
                                        throw "Set the DOCKER_PAT build parameter before publishing."
                                    }

                                    $dockerUser = $dockerUser.Trim()
                                    $dockerPat = $dockerPat.Trim()
                                    Remove-Item Env:DOCKER_PAT -ErrorAction SilentlyContinue

                                    $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
                                    $processStartInfo.FileName = $env:DOCKER_EXE
                                    $processStartInfo.Arguments = 'login --username "{0}" --password-stdin' -f $dockerUser
                                    $processStartInfo.UseShellExecute = $false
                                    $processStartInfo.RedirectStandardInput = $true
                                    $processStartInfo.CreateNoWindow = $true

                                    $dockerProcess = New-Object System.Diagnostics.Process
                                    $dockerProcess.StartInfo = $processStartInfo
                                    if (-not $dockerProcess.Start()) {
                                        throw "Unable to start Docker Hub authentication."
                                    }
                                    $dockerStarted = $true
                                    try {
                                        $dockerProcess.StandardInput.WriteLine($dockerPat)
                                        $dockerProcess.StandardInput.Flush()
                                    } finally {
                                        $dockerPat = $null
                                        $dockerProcess.StandardInput.Close()
                                    }

                                    $dockerProcess.WaitForExit()
                                    if ($dockerProcess.ExitCode -ne 0) {
                                        throw "Docker Hub authentication failed with exit code $($dockerProcess.ExitCode)."
                                    }
                                } finally {
                                    $dockerPat = $null
                                    Remove-Item Env:DOCKER_PAT -ErrorAction SilentlyContinue
                                    if ($dockerStarted -and -not $dockerProcess.HasExited) {
                                        $dockerProcess.Kill()
                                        $dockerProcess.WaitForExit()
                                    }
                                    if ($null -ne $dockerProcess) {
                                        $dockerProcess.Dispose()
                                    }
                                }
                            '''
                        }
                    }
                }
            }
        }

        stage('Docker image tagging and publishing') {
            when { expression { params.PUBLISH_IMAGE && !params.DOCKER_AUTH_DIAGNOSTIC } }
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
            when { expression { params.DEPLOY_TO_K8S && !params.DOCKER_AUTH_DIAGNOSTIC } }
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
            when { expression { params.DEPLOY_TO_K8S && !params.DOCKER_AUTH_DIAGNOSTIC } }
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
