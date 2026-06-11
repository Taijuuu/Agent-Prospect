Set-Location $PSScriptRoot

# Force UTF-8 sans BOM pour les pipes vers les executables natifs
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$envContent = Get-Content .env -Encoding UTF8

function Get-EnvVal($name) {
    $line = $envContent | Where-Object { $_ -match "^$name=" }
    if ($line) {
        $val = ($line -replace "^$name=","").TrimStart([char]0xFEFF).Trim()
        return $val
    }
    return ""
}

function Add-VercelEnv($name, $val, $env = "production") {
    if (-not $val) { Write-Host "Skip $name (vide)" -ForegroundColor Yellow; return }
    # Supprime tout BOM résiduel
    $clean = $val.TrimStart([char]0xFEFF).Trim()
    Write-Host "Adding $name..." -ForegroundColor Cyan
    $clean | vercel env add $name $env 2>&1
}

Add-VercelEnv "ANTHROPIC_API_KEY"    (Get-EnvVal "ANTHROPIC_API_KEY")
Add-VercelEnv "GOOGLE_PLACES_API_KEY" (Get-EnvVal "GOOGLE_PLACES_API_KEY")
Add-VercelEnv "DEMO_MODE"            (Get-EnvVal "DEMO_MODE")
Add-VercelEnv "DEFAULT_CITIES"       (Get-EnvVal "DEFAULT_CITIES")
Add-VercelEnv "DEFAULT_SECTORS"      (Get-EnvVal "DEFAULT_SECTORS")
Add-VercelEnv "MAX_PROSPECTS_PER_RUN" (Get-EnvVal "MAX_PROSPECTS_PER_RUN")
Add-VercelEnv "MIN_WEBSITE_SCORE"    (Get-EnvVal "MIN_WEBSITE_SCORE")
Add-VercelEnv "MY_NAME"              (Get-EnvVal "MY_NAME")
Add-VercelEnv "MY_TITLE"             (Get-EnvVal "MY_TITLE")
Add-VercelEnv "MY_PHONE"             (Get-EnvVal "MY_PHONE")
Add-VercelEnv "MY_WEBSITE"           (Get-EnvVal "MY_WEBSITE")
Add-VercelEnv "TIMEZONE"             (Get-EnvVal "TIMEZONE")
Add-VercelEnv "FOLLOW_UP_DELAY_DAYS" (Get-EnvVal "FOLLOW_UP_DELAY_DAYS")
Add-VercelEnv "DAILY_EMAIL_SEND_LIMIT" (Get-EnvVal "DAILY_EMAIL_SEND_LIMIT")

Write-Host "`nDone. Verifying..." -ForegroundColor Green
vercel env ls 2>&1
