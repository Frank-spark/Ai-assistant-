#!/usr/bin/env python3
"""Kubernetes Deployment Script for Reflex Executive Assistant."""

import argparse
import subprocess
import sys
import time
import yaml
from pathlib import Path

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def print_status(message):
    """Print status message."""
    print(f"{BLUE}[INFO]{NC} {message}")


def print_success(message):
    """Print success message."""
    print(f"{GREEN}[SUCCESS]{NC} {message}")


def print_warning(message):
    """Print warning message."""
    print(f"{YELLOW}[WARNING]{NC} {message}")


def print_error(message):
    """Print error message."""
    print(f"{RED}[ERROR]{NC} {message}")


def run_command(command, description, capture_output=True):
    """Run a command and handle errors."""
    print_status(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    
    try:
        if capture_output:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            print_success(f"{description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            result = subprocess.run(command, check=True)
            print_success(f"{description} completed successfully")
            return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def check_kubectl():
    """Check if kubectl is available and configured."""
    try:
        result = subprocess.run(["kubectl", "version", "--client"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success("kubectl is available")
            return True
        else:
            print_error("kubectl is not available")
            return False
    except FileNotFoundError:
        print_error("kubectl is not installed")
        return False


def check_cluster():
    """Check if Kubernetes cluster is accessible."""
    try:
        result = subprocess.run(["kubectl", "cluster-info"], capture_output=True, text=True)
        if result.returncode == 0:
            print_success("Kubernetes cluster is accessible")
            return True
        else:
            print_error("Cannot access Kubernetes cluster")
            return False
    except Exception as e:
        print_error(f"Error checking cluster: {e}")
        return False


def create_namespace():
    """Create the reflex-executive namespace."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/namespace.yaml"]
    return run_command(command, "Creating namespace and resource quotas")


def apply_configmap():
    """Apply the ConfigMap."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/configmap.yaml"]
    return run_command(command, "Applying ConfigMap")


def apply_secrets():
    """Apply the Secrets."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/secrets.yaml"]
    return run_command(command, "Applying Secrets")


def deploy_database():
    """Deploy PostgreSQL database."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/postgres.yaml"]
    return run_command(command, "Deploying PostgreSQL database")


def deploy_redis():
    """Deploy Redis cache."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/redis.yaml"]
    return run_command(command, "Deploying Redis cache")


def deploy_app():
    """Deploy the main application."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/app.yaml"]
    return run_command(command, "Deploying main application")


def deploy_celery():
    """Deploy Celery workers."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/celery.yaml"]
    return run_command(command, "Deploying Celery workers")


def deploy_ingress():
    """Deploy Ingress controller."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/ingress.yaml"]
    return run_command(command, "Deploying Ingress controller")


def deploy_monitoring():
    """Deploy monitoring stack."""
    command = ["kubectl", "apply", "-f", "deployments/k8s/monitoring.yaml"]
    return run_command(command, "Deploying monitoring stack")


def wait_for_deployment(deployment_name, namespace="reflex-executive", timeout=300):
    """Wait for deployment to be ready."""
    print_status(f"Waiting for deployment {deployment_name} to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "jsonpath={.status.readyReplicas}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                ready_replicas = int(result.stdout.strip())
                result = subprocess.run(
                    ["kubectl", "get", "deployment", deployment_name, "-n", namespace, "-o", "jsonpath={.spec.replicas}"],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    desired_replicas = int(result.stdout.strip())
                    if ready_replicas == desired_replicas:
                        print_success(f"Deployment {deployment_name} is ready")
                        return True
            
            time.sleep(10)
        except Exception as e:
            print_warning(f"Error checking deployment status: {e}")
            time.sleep(10)
    
    print_error(f"Deployment {deployment_name} did not become ready within {timeout} seconds")
    return False


def wait_for_pods(namespace="reflex-executive", timeout=300):
    """Wait for all pods to be ready."""
    print_status(f"Waiting for all pods in namespace {namespace} to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath={.items[*].status.phase}"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                pod_statuses = result.stdout.strip().split()
                if pod_statuses and all(status == "Running" for status in pod_statuses):
                    print_success(f"All pods in namespace {namespace} are ready")
                    return True
            
            time.sleep(10)
        except Exception as e:
            print_warning(f"Error checking pod status: {e}")
            time.sleep(10)
    
    print_error(f"Not all pods became ready within {timeout} seconds")
    return False


def check_services():
    """Check if all services are running."""
    print_status("Checking service status...")
    
    services = [
        "postgres-db",
        "redis-cache", 
        "reflex-executive-app",
        "prometheus",
        "grafana"
    ]
    
    all_healthy = True
    for service in services:
        try:
            result = subprocess.run(
                ["kubectl", "get", "service", service, "-n", "reflex-executive"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print_success(f"Service {service} is running")
            else:
                print_error(f"Service {service} is not running")
                all_healthy = False
        except Exception as e:
            print_error(f"Error checking service {service}: {e}")
            all_healthy = False
    
    return all_healthy


def get_pod_logs(pod_name, namespace="reflex-executive", lines=50):
    """Get logs from a specific pod."""
    print_status(f"Getting logs from pod {pod_name}...")
    
    command = ["kubectl", "logs", pod_name, "-n", namespace, "--tail", str(lines)]
    return run_command(command, f"Getting logs from {pod_name}", capture_output=False)


def port_forward_service(service_name, local_port, service_port, namespace="reflex-executive"):
    """Set up port forwarding for a service."""
    print_status(f"Setting up port forwarding for {service_name}...")
    
    command = ["kubectl", "port-forward", f"service/{service_name}", f"{local_port}:{service_port}", "-n", namespace]
    return run_command(command, f"Port forwarding {service_name}", capture_output=False)


def scale_deployment(deployment_name, replicas, namespace="reflex-executive"):
    """Scale a deployment to a specific number of replicas."""
    print_status(f"Scaling deployment {deployment_name} to {replicas} replicas...")
    
    command = ["kubectl", "scale", "deployment", deployment_name, f"--replicas={replicas}", "-n", namespace]
    return run_command(command, f"Scaling {deployment_name}")


def rollback_deployment(deployment_name, namespace="reflex-executive"):
    """Rollback a deployment to the previous version."""
    print_status(f"Rolling back deployment {deployment_name}...")
    
    command = ["kubectl", "rollout", "undo", "deployment", deployment_name, "-n", namespace]
    return run_command(command, f"Rolling back {deployment_name}")


def get_deployment_status(namespace="reflex-executive"):
    """Get status of all deployments."""
    print_status("Getting deployment status...")
    
    command = ["kubectl", "get", "deployments", "-n", namespace]
    return run_command(command, "Getting deployment status")


def get_pod_status(namespace="reflex-executive"):
    """Get status of all pods."""
    print_status("Getting pod status...")
    
    command = ["kubectl", "get", "pods", "-n", namespace"]
    return run_command(command, "Getting pod status")


def get_service_status(namespace="reflex-executive"):
    """Get status of all services."""
    print_status("Getting service status...")
    
    command = ["kubectl", "get", "services", "-n", namespace]
    return run_command(command, "Getting service status")


def delete_deployment():
    """Delete the entire deployment."""
    print_warning("This will delete the entire Reflex Executive Assistant deployment!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != "yes":
        print_status("Deletion cancelled")
        return True
    
    print_status("Deleting deployment...")
    
    # Delete in reverse order
    components = [
        "monitoring.yaml",
        "ingress.yaml", 
        "celery.yaml",
        "app.yaml",
        "redis.yaml",
        "postgres.yaml",
        "secrets.yaml",
        "configmap.yaml",
        "namespace.yaml"
    ]
    
    all_deleted = True
    for component in components:
        command = ["kubectl", "delete", "-f", f"deployments/k8s/{component}", "--ignore-not-found=true"]
        if not run_command(command, f"Deleting {component}"):
            all_deleted = False
    
    return all_deleted


def deploy_all():
    """Deploy all components."""
    print_status("Starting complete deployment of Reflex Executive Assistant...")
    
    deployment_steps = [
        ("Creating namespace", create_namespace),
        ("Applying ConfigMap", apply_configmap),
        ("Applying Secrets", apply_secrets),
        ("Deploying PostgreSQL", deploy_database),
        ("Deploying Redis", deploy_redis),
        ("Deploying main application", deploy_app),
        ("Deploying Celery workers", deploy_celery),
        ("Deploying Ingress", deploy_ingress),
        ("Deploying monitoring", deploy_monitoring)
    ]
    
    all_successful = True
    for step_name, step_function in deployment_steps:
        print(f"\n{'='*60}")
        print(f"Step: {step_name}")
        print(f"{'='*60}")
        
        if not step_function():
            print_error(f"Failed to {step_name.lower()}")
            all_successful = False
            break
    
    if all_successful:
        print(f"\n{'='*60}")
        print("DEPLOYMENT SUMMARY")
        print(f"{'='*60}")
        
        # Wait for deployments to be ready
        print_status("Waiting for deployments to be ready...")
        deployments = [
            "postgres-db",
            "redis-cache",
            "reflex-executive-app", 
            "reflex-executive-celery",
            "reflex-executive-celery-beat",
            "prometheus",
            "grafana"
        ]
        
        for deployment in deployments:
            if not wait_for_deployment(deployment):
                print_error(f"Deployment {deployment} failed to become ready")
                all_successful = False
        
        # Check services
        if not check_services():
            print_error("Some services are not running")
            all_successful = False
        
        # Get final status
        get_deployment_status()
        get_pod_status()
        get_service_status()
        
        if all_successful:
            print_success("All components deployed successfully!")
            print_status("Access points:")
            print_status("- Application: https://api.sparkrobotic.com")
            print_status("- API Documentation: https://api.sparkrobotic.com/docs")
            print_status("- Health Check: https://api.sparkrobotic.com/health")
            print_status("- Metrics: https://api.sparkrobotic.com/metrics")
            print_status("- Grafana: kubectl port-forward service/grafana 3000:3000 -n reflex-executive")
            print_status("- Prometheus: kubectl port-forward service/prometheus 9090:9090 -n reflex-executive")
        else:
            print_error("Some components failed to deploy properly")
    
    return all_successful


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Kubernetes Deployment Script for Reflex Executive Assistant")
    parser.add_argument("command", choices=[
        "deploy", "deploy-all", "delete", "status", "logs", "scale", "rollback", "port-forward"
    ], help="Deployment command to execute")
    
    parser.add_argument("--deployment", help="Deployment name for logs/scale/rollback commands")
    parser.add_argument("--replicas", type=int, help="Number of replicas for scale command")
    parser.add_argument("--service", help="Service name for port-forward command")
    parser.add_argument("--local-port", type=int, help="Local port for port-forward command")
    parser.add_argument("--service-port", type=int, help="Service port for port-forward command")
    parser.add_argument("--namespace", default="reflex-executive", help="Kubernetes namespace")
    
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_kubectl():
        print_error("kubectl is required but not available")
        return 1
    
    if not check_cluster():
        print_error("Cannot access Kubernetes cluster")
        return 1
    
    # Execute command
    success = False
    
    if args.command == "deploy":
        success = deploy_all()
    elif args.command == "deploy-all":
        success = deploy_all()
    elif args.command == "delete":
        success = delete_deployment()
    elif args.command == "status":
        success = get_deployment_status(args.namespace) and get_pod_status(args.namespace) and get_service_status(args.namespace)
    elif args.command == "logs":
        if not args.deployment:
            print_error("Deployment name is required for logs command")
            return 1
        success = get_pod_logs(args.deployment, args.namespace)
    elif args.command == "scale":
        if not args.deployment or not args.replicas:
            print_error("Deployment name and replicas are required for scale command")
            return 1
        success = scale_deployment(args.deployment, args.replicas, args.namespace)
    elif args.command == "rollback":
        if not args.deployment:
            print_error("Deployment name is required for rollback command")
            return 1
        success = rollback_deployment(args.deployment, args.namespace)
    elif args.command == "port-forward":
        if not args.service or not args.local_port or not args.service_port:
            print_error("Service name, local port, and service port are required for port-forward command")
            return 1
        success = port_forward_service(args.service, args.local_port, args.service_port, args.namespace)
    
    if success:
        print_success("Command completed successfully!")
        return 0
    else:
        print_error("Command failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 