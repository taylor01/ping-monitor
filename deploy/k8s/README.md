# Ping Monitor Kubernetes Deployment

## Prerequisites

1. kubectl configured with your DigitalOcean cluster:
   ```bash
   export KUBECONFIG=~/path/to/k8s-1-34-1-do-2-atl1-1767989941552-kubeconfig.yaml
   kubectl get nodes  # verify connection
   ```

## Deployment Steps

### 1. Deploy secrets from 1Password

Secrets are stored in 1Password and injected at deploy time using the `op` CLI:

```bash
# Make sure you're signed in to 1Password CLI
op signin

# Apply secrets (substitutes 1Password references with actual values)
op inject -i 00-namespace-secrets.yaml | kubectl apply -f -
```

The secrets are stored in: `op://Private/ping_monitor_deployment/`
- `RAILS_MASTER_KEY`
- `JWT_SECRET_KEY`

### 2. Deploy in order

```bash
# Apply CRDs first
kubectl apply -f 02-traefik-crds.yaml

# Wait a moment for CRDs to register
sleep 5

# Apply everything else
kubectl apply -f 00-namespace-secrets.yaml
kubectl apply -f 01-traefik.yaml
kubectl apply -f 03-backend.yaml
kubectl apply -f 04-frontend.yaml
kubectl apply -f 05-ingress-routes.yaml
```

Or apply all at once (after CRDs):
```bash
kubectl apply -f 02-traefik-crds.yaml
sleep 5
kubectl apply -f .
```

### 3. Get the LoadBalancer IP

```bash
kubectl get svc traefik -n ping-monitor -w
```

Wait for the EXTERNAL-IP to be assigned (may take 1-2 minutes).

### 4. Update DNS

Point your DNS records to the LoadBalancer IP:
- `api.ping-monitor.taylorcrib.com` → LoadBalancer IP
- `app.ping-monitor.taylorcrib.com` → LoadBalancer IP

### 5. Verify deployment

```bash
# Check all pods are running
kubectl get pods -n ping-monitor

# Check logs if needed
kubectl logs -n ping-monitor deployment/ping-monitor-api
kubectl logs -n ping-monitor deployment/ping-monitor-frontend
kubectl logs -n ping-monitor deployment/traefik

# Check certificate status (after DNS propagates)
kubectl logs -n ping-monitor deployment/traefik | grep -i acme
```

## Useful Commands

```bash
# Watch pod status
kubectl get pods -n ping-monitor -w

# Describe a pod for troubleshooting
kubectl describe pod -n ping-monitor <pod-name>

# Shell into the API container
kubectl exec -it -n ping-monitor deployment/ping-monitor-api -- /bin/bash

# Check PVC status
kubectl get pvc -n ping-monitor

# View Traefik dashboard (port-forward)
kubectl port-forward -n ping-monitor svc/traefik-dashboard 8080:8080
# Then visit http://localhost:8080/dashboard/

# Restart a deployment
kubectl rollout restart deployment/ping-monitor-api -n ping-monitor

# Scale frontend
kubectl scale deployment/ping-monitor-frontend -n ping-monitor --replicas=3
```

## Notes

- **SQLite persistence**: The API uses a PersistentVolumeClaim mounted at `/rails/storage`. 
  Make sure your Rails app stores the database there.
  
- **Single replica for API**: Because SQLite doesn't support concurrent writes, the API 
  deployment uses `strategy: Recreate` and a single replica.

- **Let's Encrypt staging**: If you're testing, uncomment the staging CA server line in 
  `01-traefik.yaml` to avoid rate limits.

- **Health checks**: The API expects a `/up` endpoint (Rails 7.1+ default). Adjust if your 
  app uses a different health check path.
