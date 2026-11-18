# Shadow Deployment

Traffic mirroring requires Istio or a compatible service mesh. The shadow copy runs with `SHADOW_MODE=true`, so state-changing requests return 202 and are not persisted.

```powershell
kubectl apply -f k8s/shadow.yaml
kubectl get pods -l app.kubernetes.io/name=aceest-shadow
kubectl logs deployment/aceest-shadow-copy
kubectl get virtualservices
```

The VirtualService mirrors 100% of traffic to the copy. Remove the mesh routing when testing is complete. Plain Kubernetes does not perform traffic mirroring.
