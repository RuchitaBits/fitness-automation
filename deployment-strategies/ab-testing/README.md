# A/B Testing

Header routing requires Istio or a compatible service mesh. Plain Kubernetes can expose both variants but cannot enforce this routing.

```powershell
kubectl apply -f k8s/ab-testing.yaml
kubectl get pods -l app.kubernetes.io/name=aceest-ab
kubectl get virtualservices,destinationrules
```

Requests without the beta header go to variant A. Send a beta request with:

```powershell
curl.exe -H "x-aceest-group: beta" http://<istio-ingress-address>/health
```
