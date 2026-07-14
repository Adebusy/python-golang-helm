# InfraStore

InfraStore is a technical assessment project developed in **Go (Golang)** using the **Gin HTTP web framework** and **SQLite** for persistent metadata storage.

The application is containerised with Docker and includes a Helm chart for deployment to Kubernetes.

## Technology Stack

* python
* FastAPI Web Framework
* SQLite
* Docker
* Kubernetes
* Helm

## Project Overview

The application provides APIs for:

* Obtaining an authentication token
* Uploading files
* Retrieving all stored file records
* Deleting a file record by ID
* Persisting uploaded files
* Persisting SQLite database records

The application stores:

* Uploaded files under `/app/media`
* SQLite database files under `/app/db`

---

# Local Installation Guide

## Prerequisites

Ensure the following tools are installed:

* Docker
* Python (FastAPI, Uvicorn)
* Git, if cloning from a repository
* curl or Postman for API testing

## Install and Synchronise Go Dependencies

Before building or running the application, ensure that the Go module dependencies are installed and synchronised.

From the project root directory, run:

go mod init github.com/infrastore

apt install python

apt install uvicorn


This command ensures that all required dependencies are available and that the go.mod and go.sum files are up to date.

After completing this step, proceed with building the Docker image:

docker build -t infratestchallenge/infrastore:latest .

## 1. Navigate to the Project Directory

Unzip the project folder and navigate to the InfraStore directory:

```bash
cd InfraStoreapi
```

## 2. Build the Docker Image

Build the application image:

```bash
docker build -t infratestchallenge/infrastoreapi:latest .
```

![Docker image build](image.png)

## 3. Prepare Local Persistent Storage

Create the local directories used for uploaded files and SQLite database persistence:

```bash
mkdir -p media db
```

## 4. Configure the Administrator Password

Export the administrator password as an environment variable:

```bash
export ADMIN_PASSWORD=secret123
```

## 5. Run the Docker Container

Run the application container:

```bash
docker run -it --rm \
  -p 8000:8000 \
  -e DJANGO_SUPERUSER_PASSWORD="$ADMIN_PASSWORD" \
  -e DJANGO_SUPERUSER_USERNAME=admin \
  -v "$(pwd)/media:/app/media" \
  -v "$(pwd)/db:/app/db" \
  infratestchallenge/infrastoreapi:latest
```

The application should now be available at:

```text
http://localhost:8000
```

![Running Docker container](image-1.png)

### Port Mapping

The Docker port mapping is:

```text
Host Port 8000
      |
      v
Container Port 8000
      |
      v
FastAPI Application
```

### Persistent Storage

The bind mounts provide persistent storage:

```text
Local Machine                 Container
-------------                 ---------
./media        ----------->   /app/media
./db           ----------->   /app/db
```

This ensures uploaded files and the SQLite database remain available outside the lifecycle of the container.

> **Security Note:** Credentials should not be hardcoded into container images or application source code. For Kubernetes deployment, the Helm chart creates a Kubernetes Secret and injects credentials into the application through environment variable references.

---

# API Usage

## 1. Obtain an Authentication Token

### Endpoint

```text
POST /api/token/
```

### Example Request

```bash
curl -X POST http://localhost:8000/api/token/ \
  -d "username=admin&password=secret123"
```

### Example Response

```json
{
  "token": "generated-token-value"
}
```

The returned token should be included in subsequent protected API requests:

```text
Authorization: Bearer <token>
```

## Authentication Flow

```text
POST /api/token/
        |
        v
Validate username and password
        |
        v
Generate authentication token
        |
        v
Store token
        |
        v
Return token to client
```

---

## 2. Upload a File

### Endpoint

```text
POST /api/upload/
```

### Example Request

```bash
curl -X POST http://localhost:8000/api/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@example.txt"
```

### Upload Request Flow

```text
Client uploads file
        |
        v
Gin Upload Handler
        |
        +----> Save physical file
        |      to /app/media
        |
        v
Repository.Create(...)
        |
        v
Store file metadata
in SQLite database
```

---

## 3. Retrieve All File Records

### Endpoint

```text
GET /api/files/
```

### Example Request

```bash
curl http://localhost:800/api/files/ \
  -H "Authorization: Bearer <token>"
```

### Example Response

```json
[
  {
    "id": 1,
    "file_name": "example.txt",
    "file_path": "/app/media/example.txt"
  },
  {
    "id": 2,
    "file_name": "receipt.pdf",
    "file_path": "/app/media/receipt.pdf"
  }
]
```

---


## 5. Delete a File Record

### Endpoint

```text
DELETE /api/files/:FileId
```

### Example Request

```bash
curl -X DELETE http://localhost:8000/api/files/11 \
  -H "Authorization: Bearer <token>"
```

---

# Kubernetes Deployment with Helm

The project includes a Helm chart for deploying InfraStore into a Kubernetes cluster.

## Prerequisites

Ensure the following tools are available:

* Kubernetes cluster
* kubectl
* Helm

Confirm cluster connectivity:

```bash
kubectl cluster-info
```

## 1. Install Helm

Install Helm using the method appropriate for your operating system.

For example, on a supported Debian/Ubuntu setup after configuring the official Helm package repository:

```bash
sudo apt install helm
```

Verify the installation:

```bash
helm version
```

## 2. Review the Helm Configuration

Review and update:

```text
deploymentManifest/values.yaml
```

Ensure the following values are correct:

* Container registry
* Image repository
* Image tag
* Application port
* Resource requests
* Resource limits
* Namespace configuration

Example:

```yaml
image:
  containerregistry: infratestchallenge
  repository: infrastore
  tag: latest

port: 8060

replicas: 1
```

## 3. Validate the Helm Chart

Before deployment, lint the chart:

```bash
helm lint ./deploymentManifest
```

Render and inspect the Kubernetes manifests:

```bash
helm template infrastore ./deploymentManifest
```

## 4. Deploy the Application

From the project root directory, run:

```bash
helm upgrade --install infrastore ./deploymentManifest
```

Alternatively, if you first change into the chart directory:

```bash
cd deploymentManifest
```

then run:

```bash
helm upgrade --install infrastore .
```

## 5. Verify the Deployment

Check all deployed Kubernetes resources:

```bash
kubectl get all -n infrastore-ns
```

![Kubernetes deployment](image-2.png)

Check the application pods:

```bash
kubectl get pods -n infrastore-ns
```

Check persistent storage:

```bash
kubectl get pv
kubectl get pvc -n infrastore-ns
```

Check Secrets:

```bash
kubectl get secret -n infrastore-ns
```

Check application logs:

```bash
kubectl logs -n infrastore-ns \
  deployment/infrastore-deployment
```

---

# Kubernetes Resources Installed by the Helm Chart

The Helm chart deploys the following components:

* Namespace
* Secret
* Deployment
* Service
* PersistentVolume
* PersistentVolumeClaim
* HPA

The Kubernetes Secret is used to provide sensitive application credentials without hardcoding them directly into the Deployment manifest.

---

# Infrastructure and Persistence Flow

The application uses SQLite for metadata persistence.

```text
FastAPI Application
        |
        | writes database records
        v
/app/db/infrastore.db
        |
        v
Kubernetes Volume Mount
        |
        v
PersistentVolumeClaim
infrastore-pvc
        |
        v
PersistentVolume
infrastore-pv
        |
        v
Persistent Storage
/mnt/data/infrastore
```

Uploaded files follow a similar persistence flow:

```text
FastAPI Application
        |
        | saves uploaded file
        v
/app/media
        |
        v
Persistent Storage
```

---

# Application Architecture

The application follows a layered structure:
![alt text](image-3.png)
```text
Client Request
      |
      v
FastAPI HTTP Handler
      |
      v
Authentication Middleware
      |
      v
Repository / Data Access Layer
      |
      v
SQLite Database
```

This separation keeps HTTP handling concerns independent from database access logic.

---

# Security Considerations

The project includes the following security practices:

* Application runs inside a Docker container
* Protected endpoints require Bearer token authentication
* Kubernetes Secrets are used for application credentials
* Sensitive values are injected through environment variables
* Persistent application data is stored outside the container lifecycle
