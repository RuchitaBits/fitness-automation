pipeline {
    agent any
    environment { PIP_DISABLE_PIP_VERSION_CHECK = '1' }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Install dependencies') {
    steps {
        sh '''
            python -m venv .venv
            .venv/bin/python -m pip install --upgrade pip
            .venv/bin/python -m pip install -r requirements.txt
        '''
    }
}
        stage('Syntax check') { steps { sh '.venv/bin/python -m compileall -q .' } }
        stage('Unit tests') { steps {sh '.venv/bin/python -m pytest -q' } }
        stage('Docker build') { steps { sh 'docker build -t aceest-fitness-devops:${BUILD_NUMBER} .' } }
        stage('Container test') { steps { sh 'docker run --rm aceest-fitness-devops:${BUILD_NUMBER} python -m pytest -q' } }
    }
    post {
        always { sh 'docker image rm aceest-fitness-devops:${BUILD_NUMBER} || true' }
    }
}
