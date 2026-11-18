# Blue-Green Deployment

```powershell
kubectl apply -f k8s/deployment-blue.yaml
kubectl apply -f k8s/deployment-green.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods
kubectl get endpoints aceest-service
```

Deploy the candidate to the inactive deployment and verify it. Use the helper to switch the Service track only after the target is ready:

```powershell
.\scripts\switch-blue-green.ps1 -Target green
```

Roll back by selecting `blue`:

```powershell
.\scripts\switch-blue-green.ps1 -Target blue
```
