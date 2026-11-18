# Canary Deployment

Plain Kubernetes can run the stable and candidate Deployments, but weighted traffic requires Istio or another service mesh. Install and configure Istio before applying this manifest.

```powershell
kubectl apply -f k8s/canary.yaml
kubectl get pods -l app.kubernetes.io/name=aceest-canary
kubectl get virtualservices,destinationrules
```

The VirtualService sends 90% to `stable` and 10% to `canary`. Verify `/health` and logs for both variants, then adjust weights in the mesh configuration or remove the canary:

```powershell
kubectl scale deployment aceest-canary-candidate --replicas=0
```
