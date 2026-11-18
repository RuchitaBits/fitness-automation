# Rolling Update

Deploy version 3.2.4:

```powershell
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/rolling-update.yaml
kubectl rollout status deployment/aceest-rolling --timeout=180s
kubectl port-forward service/aceest-rolling-service 18080:80
```

Update to 3.2.5:

```powershell
kubectl set image deployment/aceest-rolling aceest=USERNAME/aceest-fitness:3.2.5
kubectl set env deployment/aceest-rolling APP_VERSION=3.2.5
kubectl rollout status deployment/aceest-rolling --timeout=180s
kubectl rollout history deployment/aceest-rolling
```

Verify with `kubectl get pods`, `kubectl describe deployment aceest-rolling`, and `http://127.0.0.1:18080/health`. The rolling Service is ClusterIP; `k8s/service.yaml` is for the separate blue-green setup.

Rollback:

```powershell
kubectl rollout undo deployment/aceest-rolling
kubectl rollout status deployment/aceest-rolling --timeout=180s
```
