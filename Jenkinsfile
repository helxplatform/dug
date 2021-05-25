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
                buildingTag()
            }
            steps {
                sh '''
                make build
                make publish
                '''
            }
        }
    }
}