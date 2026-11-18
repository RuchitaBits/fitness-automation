param(
    [string]$Image = "",
    [string]$Version = "3.2.4"
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw "kubectl is not installed or not on PATH."
}

kubectl apply -f k8s/pvc.yaml
if ($LASTEXITCODE -ne 0) { throw "Unable to create the PVC." }

kubectl get secret aceest-secrets
if ($LASTEXITCODE -ne 0) {
    throw "Create aceest-secrets before deployment (see README.md)."
}

kubectl apply -f k8s/rolling-update.yaml
if ($LASTEXITCODE -ne 0) { throw "Unable to apply the rolling deployment." }

if ($Image) {
    kubectl set image deployment/aceest-rolling aceest=$Image
    if ($LASTEXITCODE -ne 0) { throw "Unable to set the deployment image." }
}

kubectl set env deployment/aceest-rolling APP_VERSION=$Version
kubectl rollout status deployment/aceest-rolling --timeout=180s
if ($LASTEXITCODE -ne 0) { throw "Rolling deployment did not become ready." }

Write-Host "Deployment ready. Run: kubectl port-forward service/aceest-rolling-service 18080:80"
