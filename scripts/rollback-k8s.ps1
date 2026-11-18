param(
    [string]$DeploymentName = "aceest-rolling"
)

$ErrorActionPreference = "Stop"

& kubectl rollout undo "deployment/$DeploymentName"
if ($LASTEXITCODE -ne 0) {
    throw "Could not roll back deployment $DeploymentName."
}

& kubectl rollout status "deployment/$DeploymentName" --timeout=180s
if ($LASTEXITCODE -ne 0) {
    throw "Rollback of $DeploymentName did not become ready."
}

& kubectl get deployment $DeploymentName
if ($LASTEXITCODE -ne 0) {
    throw "Could not verify deployment $DeploymentName after rollback."
}

Write-Output "Rollback completed and the deployment is ready."
