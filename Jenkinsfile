pipeline {
    agent any
    stages {
        stage('Install') {
            steps {
                sh '''
                make install
                '''
            }
        }
        stage('Test') {
            steps {
                sh '''
                make test
                '''
            }
        }
        stage('Build') {
            when {
                branch('master', 'develop')
            }
            steps {
                sh '''
                make build
                '''
            }
        }
    }
}