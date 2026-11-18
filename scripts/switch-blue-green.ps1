param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("blue", "green")]
    [string]$Target
)

$ErrorActionPreference = "Stop"

function Invoke-Kubectl {
    param([string[]]$Arguments)

    & kubectl @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "kubectl failed: $($Arguments -join ' ')"
    }
}

$service = kubectl get service aceest-service -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Could not read the aceest-service selector."
}

$selectorKey = "app.kubernetes.io/track"
$previous = $service.spec.selector.$selectorKey
if ($previous -notin @("blue", "green")) {
    throw "Service selector has no known active color; refusing an unsafe switch."
}

if ($Target -eq $previous) {
    Write-Output "Traffic already targets $Target."
    exit 0
}

Invoke-Kubectl @("rollout", "status", "deployment/aceest-$Target", "--timeout=180s")
Invoke-Kubectl @(
    "wait",
    "--for=condition=Ready",
    "pod",
    "--selector=app.kubernetes.io/name=aceest,app.kubernetes.io/track=$Target",
    "--timeout=180s"
)

$patch = @{
    spec = @{
        selector = @{
            "app.kubernetes.io/name" = "aceest"
            "app.kubernetes.io/track" = $Target
        }
    }
} | ConvertTo-Json -Depth 5 -Compress

try {
    Invoke-Kubectl @("patch", "service", "aceest-service", "--type=merge", "-p", $patch)

    $hasEndpoints = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        $endpoints = kubectl get endpoints aceest-service -o json | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) {
            throw "Could not verify service endpoints after switching traffic."
        }
        if ($endpoints.subsets -and $endpoints.subsets[0].addresses) {
            $hasEndpoints = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $hasEndpoints) {
        throw "The switched service has no ready endpoints."
    }

    Write-Output "Traffic now targets $Target. Previous track: $previous."
} catch {
    $rollback = @{
        spec = @{
            selector = @{
                "app.kubernetes.io/name" = "aceest"
                "app.kubernetes.io/track" = $previous
            }
        }
    } | ConvertTo-Json -Depth 5 -Compress
    Invoke-Kubectl @("patch", "service", "aceest-service", "--type=merge", "-p", $rollback)
    throw
}
