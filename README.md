# application-code
# CI/CD Pipeline for Microservices with Jenkins, Docker & Argo CD on EKS 
“Designed and implemented a complete CI/CD pipeline for microservices deployment to Amazon EKS using Jenkins, Docker, and Argo CD, following a GitOps workflow with separate source and deployment repositories.”


“This repository demonstrates an end-to-end CI/CD pipeline for building and containerizing microservices using Jenkins and Docker. It uses a separate deployment repository with Argo CD to automatically deploy applications to an Amazon EKS cluster using a GitOps workflow.”

Set up a Jenkins pipeline to build Docker images on every code commit and push them to a container registry such as AWS ECR or Docker Hub.

Organize microservices and Kubernetes manifests in a GitOps-friendly structure using separate repositories.

Configure Argo CD to automatically sync manifests from Git and deploy applications to an Amazon EKS cluster. 🚀

**#Pipeline workflow**

1.Developer pushes code to the Source Repository.
2.Jenkins CI pipeline triggers, runs SonarQube code analysis, builds the Docker image, and pushes it to AWS ECR.
3.Jenkins updates the Kubernetes deployment.yaml with the new image tag and commits the change to the Deployment Repository.
4.Argo CD detects the update, syncs the manifests, and deploys the application to Amazon EKS.

# Final Architecture

```
Developer
   ↓
GitHub (Source Repo)
   ↓
Jenkins Pipeline
   ↓
Docker Build
   ↓
AWS ECR
   ↓
Update Deployment Repo
   ↓
ArgoCD (GitOps)
   ↓
Kubernetes (EKS)
   ↓
LoadBalancer
   ↓
Browser → HTML Website
```

5.The application becomes live on Kubernetes.

## Jenkins Installation

Create the EC2 - t2.large .. install the java and jenkins  

## Docker Installation

Jenkins needs Docker access to build Docker images during the CI pipeline.

### Commands:

```bash
sudo apt-get update
sudo apt install -y docker.io
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

---

## SonarQube Installation

Run SonarQube using Docker (recommended for lab/demo environments).

### Commands:

```bash
docker run -d --name sonarqube -p 9000:9000 sonarqube:latest
```

**Note:** You must manually generate a SonarQube token after logging into the dashboard

## Sonar Scanner Installation

Sonar Scanner is required for Jenkins to run code quality analysis.

### Commands:

```bash
wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip
sudo apt install -y unzip
unzip sonar-scanner-cli-5.0.1.3006-linux.zip
sudo mv sonar-scanner-5.0.1.3006-linux /opt/sonar-scanner

export PATH=$PATH:/opt/sonar-scanner/bin
```

---

## Trivy Installation

Trivy is used to scan Docker images for security vulnerabilities.

### **Commands:**

```bash
sudo apt-get update
sudo apt-get install -y wget gnupg lsb-release

# Create keyrings directory
sudo mkdir -p /etc/apt/keyrings

# Download and add Trivy GPG key
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | \
gpg --dearmor | sudo tee /etc/apt/keyrings/trivy.gpg > /dev/null

# Add Trivy repository
echo "deb [signed-by=/etc/apt/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | \
sudo tee /etc/apt/sources.list.d/trivy.list

# Update packages
sudo apt-get update

# Install Trivy
sudo apt-get install -y trivy
sudo mkdir -p /var/lib/jenkins/.cache/trivy/db
sudo chown -R jenkins:jenkins /var/lib/jenkins/.cache/trivy
```

---

## Install and Configure kubectl
```bash
curl -o kubectl https://s3.us-west-2.amazonaws.com/amazon-eks/1.29.0/2024-01-04/bin/linux/amd64/kubectl
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin
kubectl version --client
```

---

## Connect to Your EKS Cluster

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws configure
aws eks update-kubeconfig --name <cluster-name> --region <region>
kubectl get nodes
```

---

## Install Helm 3

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

Ensure nodes are listed and ready.

---

## Install Argo CD in EKS

Create a namespace:

```bash
kubectl create namespace argocd
```

Use this values.yaml for exposing argocd in NodePort
```yaml
# Basic Argo CD values for NodePort exposure
server:
  service:
    type: NodePort
    nodePortHttp: 30080        # optional — choose a fixed NodePort (HTTP)
    nodePortHttps: 30443       # optional — choose a fixed NodePort (HTTPS)
    ports:
      http: 80
      https: 443
  ingress:
    enabled: false
  insecure: true                # serve UI without enforcing HTTPS (for lab use)
  extraArgs:
    - --insecure                # disable TLS redirection in ArgoCD server

configs:
  cm:
    # Disable TLS redirect so UI works over plain HTTP
    server.insecure: "true"

redis:
  enabled: true

controller:
  replicas: 1
repoServer:
  replicas: 1
applicationSet:
  replicas: 1
```

Install Argo CD using the official Helm:
```bash
# Add and update the Argo Helm repo
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# Install using the NodePort values file
helm upgrade --install argocd argo/argo-cd \
  -n argocd \
  -f values.yaml
```

Verify installation:

```bash
kubectl get pods -n argocd
```

---

## Access the Argo CD UI

Access via browser:
Allow ==30080== port in Worker Node Security Group 
```
https://<ec2-publicip>:30080
```

Get the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o yaml
echo <base64secret> | base64 --decode
```

Login using:

```
Username: admin
Password: <decoded-password>
```

---

## Jenkinsfile

### code checkout

```
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }
    }
}
```
### Setting the image for build

```
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'mydockerimage'
    }

    stages {

        stage("Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    def shortHash = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG = "${BUILD_NUMBER}-${shortHash}"
                    echo "Using image tag: ${env.IMAGE_TAG}"
                }
            }
        }

    }
}
```
### added the sonarqube stage for securing the application

```
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'mydockerimage'
        SONARQUBE_SERVER = 'SonarQubeServer'
        PATH = "/opt/sonar-scanner/bin:${PATH}"
    }

    stages {

        stage("Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    def shortHash = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG = "${BUILD_NUMBER}-${shortHash}"
                    echo "Using image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh 'sonar-scanner'
                }
            }
        }

    }
}

```
### Build the docker image and Trivy image 

```
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'mydockerimage'
        SONARQUBE_SERVER = 'SonarQubeServer'
        PATH = "/opt/sonar-scanner/bin:${PATH}"
    }

    stages {

        stage("Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    def shortHash = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG = "${BUILD_NUMBER}-${shortHash}"
                    echo "Using image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh "sonar-scanner"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Using updated Image tag ${IMAGE_NAME}:${IMAGE_TAG}"

                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage('Image Scan') {
            steps {
                sh "trivy image ${IMAGE_NAME}:${IMAGE_TAG} > report.txt"
            }
        }

    }
}

```

### Push to ECR in Aws

```
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'mydockerimage'
        SONARQUBE_SERVER = 'SonarQubeServer'
        PATH = "/opt/sonar-scanner/bin:${PATH}"
        ECR_REPO = '951532862358.dkr.ecr.us-east-1.amazonaws.com/myecrrepo'
        AWS_REGION = 'us-east-1'
    }

    stages {

        stage("Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    def shortHash = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG = "${BUILD_NUMBER}-${shortHash}"
                    echo "Using image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh "sonar-scanner"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Using updated Image tag ${IMAGE_NAME}:${IMAGE_TAG}"

                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage('Image Scan') {
            steps {
                sh "trivy image ${IMAGE_NAME}:${IMAGE_TAG} > report.txt"
            }
        }

        stage('Push to ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-cred']]) {
                    sh '''
                        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO
                        docker tag $IMAGE_NAME:$IMAGE_TAG $ECR_REPO:$IMAGE_TAG
                        docker push $ECR_REPO:$IMAGE_TAG

                        docker tag $IMAGE_NAME:$IMAGE_TAG $ECR_REPO:latest
                        docker push $ECR_REPO:latest
                    '''
                }
            }
        }

    }
}
```

### Final Jenkinsfile
```
pipeline {
    agent any

    environment {
        IMAGE_NAME = 'mydockerimage'
        SONARQUBE_SERVER = 'SonarQubeServer'
        PATH = "/opt/sonar-scanner/bin:${PATH}"
        ECR_REPO = '951532862358.dkr.ecr.us-east-1.amazonaws.com/myecrrepo'
        AWS_REGION = 'us-east-1'
        DEPLOYMENT_REPO = 'https://github.com/yaserarabth/Application-Code.git'
    }

    stages {

        stage("Checkout") {
            steps {
                git branch: 'main',
                    credentialsId: 'git-cred',
                    url: 'https://github.com/yaserarabth/Application-Code.git'
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    def shortHash = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG = "${BUILD_NUMBER}-${shortHash}"
                    echo "Using image tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh "sonar-scanner"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "Using updated Image tag ${IMAGE_NAME}:${IMAGE_TAG}"

                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
            }
        }

        stage('Image Scan') {
            steps {
                sh "trivy image ${IMAGE_NAME}:${IMAGE_TAG} > report.txt"
            }
        }

        stage('Push to ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-cred']]) {
                    sh '''
                        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO
                        docker tag $IMAGE_NAME:$IMAGE_TAG $ECR_REPO:$IMAGE_TAG
                        docker push $ECR_REPO:$IMAGE_TAG

                        docker tag $IMAGE_NAME:$IMAGE_TAG $ECR_REPO:latest
                        docker push $ECR_REPO:latest
                    '''
                }
            }
        }

        stage('Update GitOps Repo') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'git-cred',
                    usernameVariable: 'GIT_USERNAME',
                    passwordVariable: 'GIT_PASSWORD'
                )]) {
                    sh '''
                        rm -rf gitops-repo
                        git clone https://$GIT_USERNAME:$GIT_PASSWORD@github.com/Reshufowzi/deployment-repo.git gitops-repo

                        cd gitops-repo/k8s || exit 1

                        echo "Before update:"
                        grep image deployment.yaml

                        sed -i "s#image: ${ECR_REPO}:.*#image: ${ECR_REPO}:${IMAGE_TAG}#g" deployment.yaml

                        echo "After update:"
                        grep image deployment.yaml

                        git config user.email "jenkins@local"
                        git config user.name "Jenkins"

                        git add deployment.yaml
                        git commit -m "Update image tag to ${IMAGE_TAG} (Build ${BUILD_NUMBER})" || echo "No changes to commit"
                        git push origin main
                    '''
                }
            }
        }

    }
}

```
