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
        ephemeral-storage: "4Gi"
      limits:
        cpu: "1024m"
        memory: "2048Mi"
        ephemeral-storage: "8Gi"
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
        REGISTRY = "${env.REGISTRY}"
        REG_OWNER="helxplatform"
        REG_APP="dug"
        COMMIT_HASH="${sh(script:"git rev-parse --short HEAD", returnStdout: true).trim()}"
        VERSION_FILE="src/dug/_version.py"
        VERSION="${sh(script:'awk \'{ print $3 }\' src/dug/_version.py | xargs', returnStdout: true).trim()}"
        IMAGE_NAME="${REGISTRY}/${REG_OWNER}/${REG_APP}"
        TAG1="$BRANCH_NAME"
        TAG2="$COMMIT_HASH"
        TAG3="$VERSION"
        TAG4="latest"
    }
    stages {
        stage('Build') {
            steps {
                container(name: 'kaniko', shell: '/busybox/sh') {
                    sh '''#!/busybox/sh
                       echo "Build stage"
                       /kaniko/executor --dockerfile ./Dockerfile \
                                         --context . \
                                         --verbosity debug \
                                         --no-push \
                                         --destination $IMAGE_NAME:$TAG1 \
                                         --destination $IMAGE_NAME:$TAG2 \
                                         --destination $IMAGE_NAME:$TAG3 \
                                         --destination $IMAGE_NAME:$TAG4 \
                                         --tarPath image.tar
                       '''
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'image.tar', onlyIfSuccessful: true
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
        stage('Publish') {
            steps {
                container(name: 'crane', shell: '/busybox/sh') {
                    sh '''
                    echo "Publish stage"
                    echo "$DOCKERHUB_CREDS_PSW" | crane auth login -u $DOCKERHUB_CREDS_USR --password-stdin $REGISTRY
                    crane push image.tar $IMAGE_NAME:$TAG1
                    crane push image.tar $IMAGE_NAME:$TAG2
                    if [ $BRANCH_NAME == "develop" ]; then
                        crane push image.tar $IMAGE_NAME:$TAG3
                    elif [ $BRANCH_NAME == "master" ]; then
                        crane push image.tar $IMAGE_NAME:$TAG3
                        crane push image.tar $IMAGE_NAME:$TAG4
                        if [ $(git tag -l "$VERSION") ]; then
                            echo "ERROR: Tag with version $VERSION already exists! Exiting."
                        else
                            # Recover some things we've lost:
                            git config --global user.email "helx-dev@lists"
                            git config --global user.name "rencibuild rencibuild"
                            grep url .git/config
                            git checkout $BRANCH_NAME

                            # Set the tag
                            SHA=$(git log --oneline | head -1 | awk '{print $1}')
                            git tag $VERSION "$SHA"
                            git remote set-url origin https://$GITHUB_CREDS_PSW@github.com/helxplatform/dug.git
                            git push origin --tags
                        fi
                    fi
                    '''
                }
            }
        }
    }
}
