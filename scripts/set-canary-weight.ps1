param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(0, 50)]
    [int]$CanaryPercent
)

$ErrorActionPreference = "Stop"

& kubectl rollout status deployment/aceest-canary-candidate --timeout=180s
if ($LASTEXITCODE -ne 0) {
    throw "Canary candidate is not ready; traffic was not changed."
}

$stablePercent = 100 - $CanaryPercent
$patch = @{
    spec = @{
        http = @(
            @{
                route = @(
                    @{
                        destination = @{
                            host = "aceest-canary"
                            subset = "stable"
                        }
                        weight = $stablePercent
                    },
                    @{
                        destination = @{
                            host = "aceest-canary"
                            subset = "canary"
                        }
                        weight = $CanaryPercent
                    }
                )
            }
        )
    }
} | ConvertTo-Json -Depth 8 -Compress

& kubectl patch virtualservice aceest-canary --type=merge -p $patch
if ($LASTEXITCODE -ne 0) {
    throw "Could not update the canary traffic weights."
}

Write-Output "Traffic split updated: stable=$stablePercent%, canary=$CanaryPercent%."
