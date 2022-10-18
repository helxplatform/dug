library 'pipeline-utils@master'

pipeline {
  agent {
    kubernetes {
        label 'kaniko-build-agent'
        yaml """
kind: Pod
metadata:
  name: kaniko
spec:
  containers:
  - name: jnlp
    workingDir: /home/jenkins/agent/
  - name: kaniko
    workingDir: /home/jenkins/agent/
    image: gcr.io/kaniko-project/executor:debug
    imagePullPolicy: Always
    resources:
      requests:
        cpu: "512m"
        memory: "1024Mi"
        ephemeral-storage: "2Gi"
      limits:
        cpu: "1024m"
        memory: "2048Mi"
        ephemeral-storage: "2Gi"
    command:
    - /busybox/cat
    tty: true
    volumeMounts:
    - name: jenkins-docker-cfg
      mountPath: /kaniko/.docker
  - name: crane
    workingDir: /tmp/jenkins
    image: gcr.io/go-containerregistry/crane:debug
    imagePullPolicy: Always
    command:
    - /busybox/cat
    tty: true
  volumes:
  - name: jenkins-docker-cfg
    projected:
      sources:
      - secret:
          name: rencibuild-imagepull-secret
          items:
            - key: .dockerconfigjson
              path: config.json
"""
        }
    }
    environment {
        PATH = "/busybox:/kaniko:/ko-app/:$PATH"
        DOCKERHUB_CREDS = credentials("${env.CONTAINERS_REGISTRY_CREDS_ID_STR}")
        GITHUB_CREDS = credentials("${env.GITHUB_CREDS_ID_STR}")
        REGISTRY = "${env.REGISTRY}"
        REG_OWNER="helxplatform"
        REPO_NAME="dug"
        COMMIT_HASH="${sh(script:"git rev-parse --short HEAD", returnStdout: true).trim()}"
        IMAGE_NAME="${REGISTRY}/${REG_OWNER}/${REPO_NAME}"
    }
    stages {
        stage('Build') {
            steps {
                script {
                    container(name: 'go', shell: '/bin/bash') {
                        if (BRANCH_NAME.equals("master")) { 
                            CCV = go.ccv()
                        }
                    }
                    container(name: 'kaniko', shell: '/busybox/sh') {
                        def tagsToPush = ["$IMAGE_NAME:$BRANCH_NAME", "$IMAGE_NAME:$COMMIT_HASH"]
                        if (CCV != null && !CCV.trim().isEmpty() && BRANCH_NAME.equals("master")) {
                            tagsToPush.add("$IMAGE_NAME:$CCV")
                            tagsToPush.add("$IMAGE_NAME:latest")
                        } else if (BRANCH_NAME.equals("develop")) {
                            def now = new Date()
                            def currTimestamp = now.format("yyyy-MM-dd'T'HH.mm'Z'", TimeZone.getTimeZone('UTC'))
                            tagsToPush.add("$IMAGE_NAME:$currTimestamp")
                        }
                        kaniko.buildAndPush("./Dockerfile", tagsToPush)
                    }
                }
            }
        }
        stage('Test') {
            steps {
                sh '''
                echo "Test stage"
                '''
            }
        }
    }
}
