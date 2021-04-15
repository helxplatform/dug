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
        stage('Publish') {
            when {
                branch 'develop'
            }
            steps {
                sh '''
                make build.image
                make publish.image
                '''
            }
        }
    }
}