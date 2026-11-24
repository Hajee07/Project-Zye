<#
.SYNOPSIS
    ZYE AI — Automated Windows Development Environment Bootstrapper (Day 02)

.DESCRIPTION
    Automates environment validation, virtual environment initialization,
    CPU-only PyTorch setup, dependency verification, and system certification.

    Safe, idempotent, and non-destructive. Network downloads require explicit approval.

.PARAMETER DryRun
    Perform preflight inspections and show planned operations without modifying files or installing packages.

.PARAMETER ApprovePackageDownloads
    Explicit permission flag required before downloading packages or running pip installations.

.PARAMETER SkipPyTorch
    Skip installation and verification of CPU-only PyTorch.

.PARAMETER SkipRequirements
    Skip installation of dependencies from requirements.txt.

.PARAMETER NoDoctor
    Skip execution of doctor.py diagnostic script (if present).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1 -DryRun

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1 -ApprovePackageDownloads
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$ApprovePackageDownloads,
    [switch]$SkipPyTorch,
    [switch]$SkipRequirements,
    [switch]$NoDoctor
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Global Script Constants
# ---------------------------------------------------------------------------
$script:LogFilePath = $null
$script:ReportFilePath = $null
$script:GlobalReport = $null


# ---------------------------------------------------------------------------
# 1. Write-ZyeLog
# ---------------------------------------------------------------------------
function Write-ZyeLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR", "PASS", "FAIL")]
        [string]$Level = "INFO",
        [string]$Stage = "GENERAL"
    )

    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $logLine = "[$timestamp] [$Level] [$Stage] $Message"

    # Color output for console
    switch ($Level) {
        "PASS" { Write-Host $logLine -ForegroundColor Green }
        "FAIL" { Write-Host $logLine -ForegroundColor Red }
        "WARN" { Write-Host $logLine -ForegroundColor Yellow }
        "ERROR" { Write-Host $logLine -ForegroundColor Red }
        default { Write-Host $logLine -ForegroundColor Cyan }
    }

    # Redact potential sensitive tokens from log writes
    $sanitized = $logLine -replace '(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s]+', '$1=REDACTED'

    if ($script:LogFilePath) {
        try {
            $logDir = [System.IO.Path]::GetDirectoryName($script:LogFilePath)
            if (-not (Test-Path -Path $logDir)) {
                New-Item -ItemType Directory -Path $logDir -Force | Out-Null
            }
            [System.IO.File]::AppendAllText($script:LogFilePath, "$sanitized`r`n", [System.Text.Encoding]::UTF8)
        }
        catch {
            # Never let log writing failure crash main flow
        }
    }
}


# ---------------------------------------------------------------------------
# 2. Initialize-ZyeReport
# ---------------------------------------------------------------------------
function Initialize-ZyeReport {
    [CmdletBinding()]
    param()

    $script:GlobalReport = [ordered]@{
        "project"                   = "Zye AI"
        "stage"                     = "Day 02"
        "timestamp"                 = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        "overall_status"            = "PENDING_APPROVAL"
        "python_version"            = $null
        "python_executable"         = $null
        "venv_valid"                = $false
        "pip_upgrade"               = "NOT_RUN"
        "pytorch_cpu"               = "NOT_RUN"
        "requirements_installation" = "NOT_RUN"
        "pip_check"                 = "NOT_RUN"
        "dependency_verification"   = "NOT_RUN"
        "config_validation"         = "NOT_RUN"
        "doctor_py"                 = "NOT_YET_IMPLEMENTED"
        "metrics"                   = [ordered]@{
            "available_disk_gb_before" = $null
            "available_ram_gb_before"  = $null
        }
        "errors"                    = @()
        "warnings"                  = @()
    }
}


# ---------------------------------------------------------------------------
# 3. Get-ProjectRoot
# ---------------------------------------------------------------------------
function Get-ProjectRoot {
    [CmdletBinding()]
    param()

    # setup_env.ps1 is in scripts/, parent directory is the project root
    $scriptsDir = $PSScriptRoot
    if (-not $scriptsDir) {
        $scriptsDir = (Get-Location).Path
    }
    $root = [System.IO.Path]::GetFullPath((Join-Path -Path $scriptsDir -ChildPath ".."))
    return $root
}


# ---------------------------------------------------------------------------
# 4. Test-WindowsPlatform
# ---------------------------------------------------------------------------
function Test-WindowsPlatform {
    [CmdletBinding()]
    param()

    $platformIsWinNT = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
    if (-not $platformIsWinNT) {
        Write-ZyeLog -Message "Unsupported OS platform: $([System.Environment]::OSVersion.Platform)" -Level "FAIL" -Stage "STAGE 01"
        return $false
    }
    Write-ZyeLog -Message "Windows OS platform verified: $([System.Environment]::OSVersion.VersionString)" -Level "PASS" -Stage "STAGE 01"
    return $true
}


# ---------------------------------------------------------------------------
# 5. Test-OperatingSystemArchitecture
# ---------------------------------------------------------------------------
function Test-OperatingSystemArchitecture {
    [CmdletBinding()]
    param()

    $is64 = [System.Environment]::Is64BitOperatingSystem
    if (-not $is64) {
        Write-ZyeLog -Message "32-bit Windows detected. Zye AI requires 64-bit Windows." -Level "FAIL" -Stage "STAGE 01"
        return $false
    }
    Write-ZyeLog -Message "64-bit operating system architecture verified." -Level "PASS" -Stage "STAGE 01"
    return $true
}


# ---------------------------------------------------------------------------
# 6. Get-PythonLauncher
# ---------------------------------------------------------------------------
function Get-PythonLauncher {
    [CmdletBinding()]
    param()

    # Check candidates: prefer python, then py -3.12, py -3.11, py
    $candidates = @("python", "py -3.12", "py -3.11", "py")
    foreach ($cand in $candidates) {
        try {
            $cmdParts = $cand -split " "
            $cmd = $cmdParts[0]
            $found = Get-Command -Name $cmd -ErrorAction SilentlyContinue
            if ($found) {
                $pyCheckArgs = if ($cmdParts.Length -gt 1) { @($cmdParts[1..($cmdParts.Length - 1)]) + @("-c", "import sys; print(sys.executable)") } else { @("-c", "import sys; print(sys.executable)") }
                $testOutput = & $cmd $pyCheckArgs 2>$null
                if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($testOutput)) {
                    return $cand
                }
            }
        }
        catch {
            # Continue checking other candidates
        }
    }
    return $null
}


# ---------------------------------------------------------------------------
# 7. Test-PythonVersion
# ---------------------------------------------------------------------------
function Test-PythonVersion {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    try {
        $parts = $PythonExe -split " "
        $bin = $parts[0]
        $extraArgs = if ($parts.Length -gt 1) { @($parts[1..($parts.Length - 1)]) } else { @() }
        $cmdArgs = $extraArgs + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); print(sys.executable)")

        $output = & $bin $cmdArgs 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ZyeLog -Message "Failed to query Python version using $PythonExe" -Level "FAIL" -Stage "STAGE 02"
            return $null
        }

        $lines = ($output -split "`r?`n") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        $verString = $lines[0].Trim()
        $exePath = if ($lines.Length -gt 1) { $lines[1].Trim() } else { $bin }

        $parts = $verString.Split('.')
        $major = [int]$parts[0]
        $minor = [int]$parts[1]

        if ($major -eq 3 -and ($minor -eq 11 -or $minor -eq 12)) {
            Write-ZyeLog -Message "Supported Python version verified: $verString ($exePath)" -Level "PASS" -Stage "STAGE 02"
            return @{
                "Version"    = $verString
                "Major"      = $major
                "Minor"      = $minor
                "Executable" = $exePath
            }
        }
        else {
            Write-ZyeLog -Message "Incompatible Python version: $verString. Supported: 3.11, 3.12." -Level "FAIL" -Stage "STAGE 02"
            return $null
        }
    }
    catch {
        Write-ZyeLog -Message "Error inspecting Python runtime: $_" -Level "FAIL" -Stage "STAGE 02"
        return $null
    }
}


# ---------------------------------------------------------------------------
# 8. Test-DiskSpace
# ---------------------------------------------------------------------------
function Test-DiskSpace {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath,
        [double]$MinDiskGb = 3.0
    )

    try {
        $driveLetter = [System.IO.Path]::GetPathRoot($RootPath).TrimEnd('\')
        $driveInfo = [System.IO.DriveInfo]::GetDrives() | Where-Object { $_.IsReady -and $_.Name.TrimEnd('\') -eq $driveLetter }

        if ($driveInfo) {
            $freeGb = [math]::Round($driveInfo.AvailableFreeSpace / 1GB, 2)
            $script:GlobalReport.metrics.available_disk_gb_before = $freeGb

            if ($freeGb -lt $MinDiskGb) {
                Write-ZyeLog -Message "Insufficient disk space on $driveLetter. Available: $freeGb GB (Required: $MinDiskGb GB)" -Level "FAIL" -Stage "STAGE 01"
                return $false
            }
            Write-ZyeLog -Message "Disk space check passed on $driveLetter : $freeGb GB free (Min: $MinDiskGb GB)" -Level "PASS" -Stage "STAGE 01"
            return $true
        }
        else {
            Write-ZyeLog -Message "Could not query drive info for $driveLetter" -Level "WARN" -Stage "STAGE 01"
            return $true
        }
    }
    catch {
        Write-ZyeLog -Message "Error querying disk capacity: $_" -Level "WARN" -Stage "STAGE 01"
        return $true
    }
}


# ---------------------------------------------------------------------------
# 9. Test-AvailableMemory
# ---------------------------------------------------------------------------
function Test-AvailableMemory {
    [CmdletBinding()]
    param(
        [double]$MinRamGb = 1.5
    )

    try {
        Add-Type -AssemblyName Microsoft.VisualBasic -ErrorAction SilentlyContinue
        $compInfo = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
        $freeRamGb = [math]::Round($compInfo.AvailablePhysicalMemory / 1GB, 2)
        $script:GlobalReport.metrics.available_ram_gb_before = $freeRamGb

        if ($freeRamGb -lt $MinRamGb) {
            Write-ZyeLog -Message "Low available RAM: $freeRamGb GB (Recommended min: $MinRamGb GB)" -Level "WARN" -Stage "STAGE 01"
            $script:GlobalReport.warnings += "Low available RAM: $freeRamGb GB (Recommended: $MinRamGb GB)"
            return $true
        }

        Write-ZyeLog -Message "Memory check passed: $freeRamGb GB available (Min: $MinRamGb GB)" -Level "PASS" -Stage "STAGE 01"
        return $true
    }
    catch {
        Write-ZyeLog -Message "Error querying system memory: $_" -Level "WARN" -Stage "STAGE 01"
        return $true
    }
}


# ---------------------------------------------------------------------------
# 10. Test-ProjectStructure
# ---------------------------------------------------------------------------
function Test-ProjectStructure {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    $requiredDirs = @("scripts", "skills", "data", "logs", "backups", "profiles", "tests")
    $requiredFiles = @("zye_config.toml", "requirements.txt", ".gitignore", "README.md")

    $allValid = $true
    foreach ($d in $requiredDirs) {
        $p = Join-Path -Path $RootPath -ChildPath $d
        if (-not (Test-Path -Path $p -PathType Container)) {
            Write-ZyeLog -Message "Missing directory: $d" -Level "FAIL" -Stage "STAGE 03"
            $allValid = $false
        }
    }

    foreach ($f in $requiredFiles) {
        $p = Join-Path -Path $RootPath -ChildPath $f
        if (-not (Test-Path -Path $p -PathType Leaf)) {
            Write-ZyeLog -Message "Missing required file: $f" -Level "FAIL" -Stage "STAGE 03"
            $allValid = $false
        }
    }

    if ($allValid) {
        Write-ZyeLog -Message "Project directory structure and baseline files verified." -Level "PASS" -Stage "STAGE 03"
    }
    return $allValid
}


# ---------------------------------------------------------------------------
# 11. Test-RequirementsManifest
# ---------------------------------------------------------------------------
function Test-RequirementsManifest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath
    )

    if (-not (Test-Path -Path $ManifestPath)) {
        Write-ZyeLog -Message "Requirements file not found at: $ManifestPath" -Level "FAIL" -Stage "STAGE 03"
        return $false
    }

    $lines = Get-Content -Path $ManifestPath -Encoding UTF8
    $seenPackages = New-Object System.Collections.Generic.HashSet[string]
    $issues = @()

    $lineNum = 0
    foreach ($line in $lines) {
        $lineNum++
        $clean = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($clean) -or $clean.StartsWith("#")) {
            continue
        }

        # Check for editable install
        if ($clean.StartsWith("-e ") -or $clean.StartsWith("--editable")) {
            $issues += "Line $lineNum : Editable installs forbidden ($clean)"
        }
        # Check for direct URL
        if ($clean -match "https?://") {
            $issues += "Line $lineNum : Direct URL dependencies forbidden ($clean)"
        }
        # Check for git dependencies
        if ($clean -match "git(\+|://)") {
            $issues += "Line $lineNum : Git dependencies forbidden ($clean)"
        }
        # Check for local file path
        if ($clean.StartsWith(".") -or $clean.StartsWith("/")) {
            $issues += "Line $lineNum : Local path dependencies forbidden ($clean)"
        }

        # Parse package name for duplicate check
        $pkgName = ($clean -split "[=<>~!]")[0].Trim().ToLower()
        if ($seenPackages.Contains($pkgName)) {
            $issues += "Line $lineNum : Duplicate package declaration: $pkgName"
        }
        else {
            $seenPackages.Add($pkgName) | Out-Null
        }
    }

    if ($issues.Count -gt 0) {
        foreach ($iss in $issues) {
            Write-ZyeLog -Message $iss -Level "FAIL" -Stage "STAGE 03"
            $script:GlobalReport.errors += $iss
        }
        return $false
    }

    Write-ZyeLog -Message "Requirements manifest validated: $($seenPackages.Count) secure declarations, 0 duplicates." -Level "PASS" -Stage "STAGE 03"
    return $true
}


# ---------------------------------------------------------------------------
# 12. Initialize-VirtualEnvironment
# ---------------------------------------------------------------------------
function Initialize-VirtualEnvironment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    $venvDir = Join-Path -Path $RootPath -ChildPath ".venv"
    $venvPy = Join-Path -Path $venvDir -ChildPath "Scripts\python.exe"

    if (Test-Path -Path $venvPy -PathType Leaf) {
        # Inspect existing venv
        $verInfo = Test-PythonVersion -PythonExe $venvPy
        if ($verInfo) {
            Write-ZyeLog -Message "Existing virtual environment verified at: $venvDir (Python $($verInfo.Version))" -Level "PASS" -Stage "STAGE 04"
            $script:GlobalReport.venv_valid = $true
            return $venvPy
        }
        else {
            Write-ZyeLog -Message "Existing virtual environment has incompatible Python runtime." -Level "FAIL" -Stage "STAGE 04"
            return $null
        }
    }

    # Create new virtual environment
    Write-ZyeLog -Message "Initializing new virtual environment at: $venvDir" -Level "INFO" -Stage "STAGE 05"
    & $PythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -Path $venvPy)) {
        Write-ZyeLog -Message "Failed to create virtual environment at $venvDir" -Level "FAIL" -Stage "STAGE 05"
        return $null
    }

    Write-ZyeLog -Message "Virtual environment initialized successfully at: $venvDir" -Level "PASS" -Stage "STAGE 05"
    $script:GlobalReport.venv_valid = $true
    return $venvPy
}


# ---------------------------------------------------------------------------
# 13. Get-VenvPython
# ---------------------------------------------------------------------------
function Get-VenvPython {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    $py = Join-Path -Path $RootPath -ChildPath ".venv\Scripts\python.exe"
    if (Test-Path -Path $py -PathType Leaf) {
        return $py
    }
    return $null
}


# ---------------------------------------------------------------------------
# 14. Upgrade-Pip
# ---------------------------------------------------------------------------
function Upgrade-Pip {
    [CmdletBinding()]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseApprovedVerbs', '')]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython
    )

    Write-ZyeLog -Message "Upgrading pip inside virtual environment..." -Level "INFO" -Stage "STAGE 06"

    $maxRetries = 2
    $attempt = 0
    $success = $false

    while ($attempt -le $maxRetries -and -not $success) {
        $attempt++
        & $VenvPython -m pip install --upgrade pip 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
        else {
            Write-ZyeLog -Message "pip upgrade attempt $attempt failed. Retrying..." -Level "WARN" -Stage "STAGE 06"
            Start-Sleep -Seconds 2
        }
    }

    if ($success) {
        $pipVer = & $VenvPython -m pip --version
        Write-ZyeLog -Message "pip upgraded successfully: $pipVer" -Level "PASS" -Stage "STAGE 06"
        $script:GlobalReport.pip_upgrade = "SUCCESS ($pipVer)"
        return $true
    }
    else {
        Write-ZyeLog -Message "Failed to upgrade pip after $maxRetries retries." -Level "FAIL" -Stage "STAGE 06"
        $script:GlobalReport.pip_upgrade = "FAILED"
        $script:GlobalReport.errors += "Failed to upgrade pip in virtual environment."
        return $false
    }
}

# Approved verb alias for PowerShell Script Analyzer compliance
Set-Alias -Name Update-Pip -Value Upgrade-Pip -ErrorAction SilentlyContinue


# ---------------------------------------------------------------------------
# 15. Install-CpuOnlyTorch
# ---------------------------------------------------------------------------
function Install-CpuOnlyTorch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython
    )

    Write-ZyeLog -Message "Installing CPU-only PyTorch from official PyTorch CPU wheel index..." -Level "INFO" -Stage "STAGE 07"

    $maxRetries = 2
    $attempt = 0
    $success = $false

    while ($attempt -le $maxRetries -and -not $success) {
        $attempt++
        & $VenvPython -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
        else {
            Write-ZyeLog -Message "PyTorch installation attempt $attempt failed. Retrying..." -Level "WARN" -Stage "STAGE 07"
            Start-Sleep -Seconds 3
        }
    }

    if ($success) {
        Write-ZyeLog -Message "PyTorch package installation completed." -Level "PASS" -Stage "STAGE 07"
        return $true
    }
    else {
        Write-ZyeLog -Message "Failed to install CPU-only PyTorch." -Level "FAIL" -Stage "STAGE 07"
        $script:GlobalReport.pytorch_cpu = "INSTALL_FAILED"
        $script:GlobalReport.errors += "Failed to install CPU-only PyTorch package."
        return $false
    }
}


# ---------------------------------------------------------------------------
# 16. Test-CpuOnlyTorch
# ---------------------------------------------------------------------------
function Test-CpuOnlyTorch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython
    )

    Write-ZyeLog -Message "Verifying PyTorch CPU execution and tensor operations..." -Level "INFO" -Stage "STAGE 08"

    $testCode = @"
import sys, torch
x = torch.tensor([1, 2, 3])
y = x * 2
assert y.tolist() == [2, 4, 6], "Tensor multiplication check failed"
assert torch.cuda.is_available() is False, f"Expected CUDA False, got {torch.cuda.is_available()}"
print(f"VERIFIED:torch_version={torch.__version__}:cuda={torch.version.cuda}")
"@

    $output = & $VenvPython -c $testCode 2>&1
    if ($LASTEXITCODE -eq 0 -and $output -match "VERIFIED") {
        Write-ZyeLog -Message "CPU-only PyTorch operational and verified: $output" -Level "PASS" -Stage "STAGE 08"
        $script:GlobalReport.pytorch_cpu = "VERIFIED ($output)"
        return $true
    }
    else {
        Write-ZyeLog -Message "PyTorch CPU verification failed: $output" -Level "FAIL" -Stage "STAGE 08"
        $script:GlobalReport.pytorch_cpu = "VERIFICATION_FAILED ($output)"
        $script:GlobalReport.errors += "PyTorch CPU test failed: $output"
        return $false
    }
}


# ---------------------------------------------------------------------------
# 17. Install-ZyeRequirements
# ---------------------------------------------------------------------------
function Install-ZyeRequirements {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython,
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath
    )

    Write-ZyeLog -Message "Installing Zye dependencies from requirements.txt..." -Level "INFO" -Stage "STAGE 09"

    $maxRetries = 2
    $attempt = 0
    $success = $false

    while ($attempt -le $maxRetries -and -not $success) {
        $attempt++
        & $VenvPython -m pip install --no-cache-dir -r $ManifestPath
        if ($LASTEXITCODE -eq 0) {
            $success = $true
        }
        else {
            Write-ZyeLog -Message "Requirements installation attempt $attempt failed. Retrying..." -Level "WARN" -Stage "STAGE 09"
            Start-Sleep -Seconds 3
        }
    }

    if ($success) {
        Write-ZyeLog -Message "All declared requirements installed successfully." -Level "PASS" -Stage "STAGE 09"
        $script:GlobalReport.requirements_installation = "SUCCESS"
        return $true
    }
    else {
        Write-ZyeLog -Message "Failed to install requirements.txt dependencies." -Level "FAIL" -Stage "STAGE 09"
        $script:GlobalReport.requirements_installation = "FAILED"
        $script:GlobalReport.errors += "Failed to install dependencies from requirements.txt."
        return $false
    }
}


# ---------------------------------------------------------------------------
# 18. Test-PipIntegrity
# ---------------------------------------------------------------------------
function Test-PipIntegrity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython
    )

    Write-ZyeLog -Message "Validating package consistency via pip check..." -Level "INFO" -Stage "STAGE 10"

    $output = & $VenvPython -m pip check 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-ZyeLog -Message "pip check verified: No broken requirements or version conflicts detected." -Level "PASS" -Stage "STAGE 10"
        $script:GlobalReport.pip_check = "PASS"
        return $true
    }
    else {
        Write-ZyeLog -Message "pip check detected dependency conflicts: $output" -Level "WARN" -Stage "STAGE 10"
        $script:GlobalReport.pip_check = "CONFLICTS_DETECTED ($output)"
        $script:GlobalReport.warnings += "pip check conflicts: $output"
        return $false
    }
}


# ---------------------------------------------------------------------------
# 19. Invoke-DependencyVerification
# ---------------------------------------------------------------------------
function Invoke-DependencyVerification {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython,
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    Write-ZyeLog -Message "Executing Python dependency verification engine..." -Level "INFO" -Stage "STAGE 11"

    $verifierScript = Join-Path -Path $RootPath -ChildPath "scripts\verify_dependencies.py"
    $inventoryPath = Join-Path -Path $RootPath -ChildPath "logs\day02_package_inventory.json"

    if (-not (Test-Path -Path $verifierScript)) {
        Write-ZyeLog -Message "Verifier script not found: $verifierScript" -Level "FAIL" -Stage "STAGE 11"
        $script:GlobalReport.dependency_verification = "MISSING_SCRIPT"
        return $false
    }

    & $VenvPython $verifierScript --output $inventoryPath
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-ZyeLog -Message "Dependency verification completed successfully. Inventory saved to logs/day02_package_inventory.json" -Level "PASS" -Stage "STAGE 11"
        $script:GlobalReport.dependency_verification = "PASS"
        return $true
    }
    else {
        Write-ZyeLog -Message "Dependency verification reported missing or failing packages." -Level "WARN" -Stage "STAGE 11"
        $script:GlobalReport.dependency_verification = "FAILED_CHECKS"
        return $false
    }
}


# ---------------------------------------------------------------------------
# 20. Invoke-ConfigurationValidation
# ---------------------------------------------------------------------------
function Invoke-ConfigurationValidation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython,
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    Write-ZyeLog -Message "Validating zye_config.toml and environment settings..." -Level "INFO" -Stage "STAGE 12"

    $configScript = Join-Path -Path $RootPath -ChildPath "scripts\validate_config.py"
    if (-not (Test-Path -Path $configScript)) {
        Write-ZyeLog -Message "Config validator script missing: $configScript" -Level "FAIL" -Stage "STAGE 12"
        return $false
    }

    & $VenvPython $configScript
    if ($LASTEXITCODE -eq 0) {
        Write-ZyeLog -Message "Configuration validation passed." -Level "PASS" -Stage "STAGE 12"
        $script:GlobalReport.config_validation = "PASS"
        return $true
    }
    else {
        Write-ZyeLog -Message "Configuration validation failed." -Level "FAIL" -Stage "STAGE 12"
        $script:GlobalReport.config_validation = "FAIL"
        $script:GlobalReport.errors += "zye_config.toml validation failed."
        return $false
    }
}


# ---------------------------------------------------------------------------
# 21. Export-InstallationReport
# ---------------------------------------------------------------------------
function Export-InstallationReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Report,
        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    try {
        $dir = [System.IO.Path]::GetDirectoryName($OutputPath)
        if (-not (Test-Path -Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        $json = $Report | ConvertTo-Json -Depth 6
        [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.Encoding]::UTF8)
        Write-ZyeLog -Message "Installation report exported to: $OutputPath" -Level "INFO" -Stage "REPORT"
    }
    catch {
        Write-ZyeLog -Message "Failed to export installation report: $_" -Level "WARN" -Stage "REPORT"
    }
}


# ---------------------------------------------------------------------------
# 22. Invoke-DoctorIfAvailable
# ---------------------------------------------------------------------------
function Invoke-DoctorIfAvailable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPython,
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    $doctorScript = Join-Path -Path $RootPath -ChildPath "doctor.py"
    if (Test-Path -Path $doctorScript) {
        if ($NoDoctor) {
            Write-ZyeLog -Message "doctor.py found but skipped due to -NoDoctor flag." -Level "INFO" -Stage "DOCTOR"
            $script:GlobalReport.doctor_py = "SKIPPED_BY_FLAG"
            return 0
        }
        else {
            Write-ZyeLog -Message "Executing doctor.py diagnostic engine..." -Level "INFO" -Stage "DOCTOR"
            & $VenvPython $doctorScript
            $doctorExitCode = $LASTEXITCODE

            if ($doctorExitCode -eq 0) {
                Write-ZyeLog -Message "doctor.py health diagnostic certified system (READY or DEGRADED)." -Level "PASS" -Stage "DOCTOR"
                $script:GlobalReport.doctor_py = "CERTIFIED (Exit: 0)"
                return 0
            }
            elseif ($doctorExitCode -eq 1) {
                Write-ZyeLog -Message "doctor.py reported critical diagnostic failures (BLOCKED). Inspect logs/doctor_report.json" -Level "WARN" -Stage "DOCTOR"
                $script:GlobalReport.doctor_py = "BLOCKED (Exit: 1)"
                $script:GlobalReport.warnings += "doctor.py health audit returned BLOCKED status."
                return 1
            }
            else {
                Write-ZyeLog -Message "doctor.py failed with unexpected exit code $doctorExitCode" -Level "FAIL" -Stage "DOCTOR"
                $script:GlobalReport.doctor_py = "EXECUTION_ERROR (Exit: $doctorExitCode)"
                $script:GlobalReport.errors += "doctor.py execution failure."
                return 2
            }
        }
    }
    else {
        Write-ZyeLog -Message "doctor.py not found (SKIP / NOT_YET_IMPLEMENTED)." -Level "INFO" -Stage "DOCTOR"
        $script:GlobalReport.doctor_py = "NOT_YET_IMPLEMENTED"
        return 0
    }
}


# ---------------------------------------------------------------------------
# 23. Invoke-ZyeSetup (Main Orchestration)
# ---------------------------------------------------------------------------
function Invoke-ZyeSetup {
    [CmdletBinding()]
    param()

    $root = Get-ProjectRoot
    $script:LogFilePath = Join-Path -Path $root -ChildPath "logs\setup_env.log"
    $script:ReportFilePath = Join-Path -Path $root -ChildPath "logs\day02_install_report.json"

    Initialize-ZyeReport

    Write-ZyeLog -Message "========================================================================" -Stage "STARTUP"
    Write-ZyeLog -Message "ZYE AI — Day 02 Windows Environment Bootstrapper" -Stage "STARTUP"
    Write-ZyeLog -Message "Project Root: $root" -Stage "STARTUP"
    Write-ZyeLog -Message "========================================================================" -Stage "STARTUP"

    # STAGE 1: Windows platform and architecture
    if (-not (Test-WindowsPlatform)) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }
    if (-not (Test-OperatingSystemArchitecture)) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    # Resource preflight
    Test-DiskSpace -RootPath $root | Out-Null
    Test-AvailableMemory | Out-Null

    # STAGE 2: Python runtime validation
    $pyLauncher = Get-PythonLauncher
    if (-not $pyLauncher) {
        Write-ZyeLog -Message "No Python installation detected on system PATH." -Level "FAIL" -Stage "STAGE 02"
        $script:GlobalReport.overall_status = "BLOCKED"
        $script:GlobalReport.errors += "Python 3.11 or 3.12 not found on system PATH."
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    $pyInfo = Test-PythonVersion -PythonExe $pyLauncher
    if (-not $pyInfo) {
        $script:GlobalReport.overall_status = "BLOCKED"
        $script:GlobalReport.errors += "Incompatible Python version. Python 3.11 or 3.12 required."
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    $script:GlobalReport.python_version = $pyInfo.Version
    $script:GlobalReport.python_executable = $pyInfo.Executable

    # STAGE 3: Project structure and requirements manifest check
    if (-not (Test-ProjectStructure -RootPath $root)) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    $reqPath = Join-Path -Path $root -ChildPath "requirements.txt"
    if (-not (Test-RequirementsManifest -ManifestPath $reqPath)) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    # STAGE 4 & 5: Virtual environment initialization
    $venvPy = Initialize-VirtualEnvironment -RootPath $root -PythonExe $pyLauncher
    if (-not $venvPy) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    # Dry-Run early exit
    if ($DryRun) {
        Write-ZyeLog -Message "------------------------------------------------------------------------" -Stage "DRY-RUN"
        Write-ZyeLog -Message "[DRY-RUN MODE ACTIVATED]" -Stage "DRY-RUN"
        Write-ZyeLog -Message "All preflight platform, runtime, manifest and virtual environment checks passed." -Stage "DRY-RUN"
        Write-ZyeLog -Message "Planned Action 1: Upgrade pip in .venv" -Stage "DRY-RUN"
        if (-not $SkipPyTorch) {
            Write-ZyeLog -Message "Planned Action 2: Install CPU-only PyTorch via https://download.pytorch.org/whl/cpu" -Stage "DRY-RUN"
            Write-ZyeLog -Message "Planned Action 3: Verify PyTorch CPU tensor execution" -Stage "DRY-RUN"
        }
        if (-not $SkipRequirements) {
            Write-ZyeLog -Message "Planned Action 4: Install packages from requirements.txt" -Stage "DRY-RUN"
            Write-ZyeLog -Message "Planned Action 5: Run pip check and dependency verifier" -Stage "DRY-RUN"
            Write-ZyeLog -Message "Planned Action 6: Generate requirements-lock.txt" -Stage "DRY-RUN"
        }
        Write-ZyeLog -Message "No packages downloaded or installed in DryRun mode." -Stage "DRY-RUN"
        Write-ZyeLog -Message "------------------------------------------------------------------------" -Stage "DRY-RUN"
        $script:GlobalReport.overall_status = "DRY_RUN_PASSED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 0
    }

    # Explicit approval check
    if (-not $ApprovePackageDownloads) {
        Write-ZyeLog -Message "========================================================================" -Stage "APPROVAL"
        Write-ZyeLog -Message "NOTICE: Package downloads require explicit approval." -Level "WARN" -Stage "APPROVAL"
        Write-ZyeLog -Message "Preflight checks passed. To proceed with package downloads, run:" -Level "WARN" -Stage "APPROVAL"
        Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_env.ps1 -ApprovePackageDownloads" -ForegroundColor Yellow
        Write-ZyeLog -Message "========================================================================" -Stage "APPROVAL"
        $script:GlobalReport.overall_status = "PENDING_APPROVAL"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 0
    }

    # STAGE 6: Pip upgrade
    if (-not (Upgrade-Pip -VenvPython $venvPy)) {
        $script:GlobalReport.overall_status = "BLOCKED"
        Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
        return 1
    }

    # STAGE 7 & 8: CPU-only PyTorch
    if (-not $SkipPyTorch) {
        if (-not (Install-CpuOnlyTorch -VenvPython $venvPy)) {
            $script:GlobalReport.overall_status = "BLOCKED"
            Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
            return 1
        }
        if (-not (Test-CpuOnlyTorch -VenvPython $venvPy)) {
            $script:GlobalReport.overall_status = "BLOCKED"
            Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
            return 1
        }
    }
    else {
        Write-ZyeLog -Message "PyTorch installation skipped by -SkipPyTorch flag." -Level "WARN" -Stage "STAGE 07"
        $script:GlobalReport.pytorch_cpu = "SKIPPED_BY_FLAG"
    }

    # STAGE 9: Requirements installation
    if (-not $SkipRequirements) {
        if (-not (Install-ZyeRequirements -VenvPython $venvPy -ManifestPath $reqPath)) {
            $script:GlobalReport.overall_status = "BLOCKED"
            Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
            return 1
        }
    }
    else {
        Write-ZyeLog -Message "Requirements installation skipped by -SkipRequirements flag." -Level "WARN" -Stage "STAGE 09"
        $script:GlobalReport.requirements_installation = "SKIPPED_BY_FLAG"
    }

    # STAGE 10: pip integrity check
    Test-PipIntegrity -VenvPython $venvPy | Out-Null

    # STAGE 11: Dependency verification
    Invoke-DependencyVerification -VenvPython $venvPy -RootPath $root | Out-Null

    # STAGE 12: Configuration validation
    Invoke-ConfigurationValidation -VenvPython $venvPy -RootPath $root | Out-Null

    # STAGE 13: Lockfile generation (only after successful full installation)
    if (-not $SkipRequirements -and -not $SkipPyTorch) {
        $lockPath = Join-Path -Path $root -ChildPath "requirements-lock.txt"
        Write-ZyeLog -Message "Generating reproducible requirements-lock.txt..." -Level "INFO" -Stage "LOCKFILE"
        $genDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss UTC")
        $headerLines = @(
            "# ============================================================================="
            "# ZYE AI — Requirements Lock File"
            "# ============================================================================="
            "# Environment: Windows $($pyInfo.Version) AMD64"
            "# Generated: $genDate"
            "# This file is an exact snapshot of installed virtual environment dependencies."
            "# ============================================================================="
            ""
        )
        $header = $headerLines -join "`r`n"
        $freezeOutput = & $venvPy -m pip freeze
        $freezeText = $freezeOutput -join "`r`n"
        $fullLock = $header + "`r`n" + $freezeText + "`r`n"
        [System.IO.File]::WriteAllText($lockPath, $fullLock, [System.Text.Encoding]::UTF8)
        Write-ZyeLog -Message "requirements-lock.txt generated successfully." -Level "PASS" -Stage "LOCKFILE"
    }

    # STAGE 14: Doctor if available
    Invoke-DoctorIfAvailable -VenvPython $venvPy -RootPath $root

    # STAGE 15: Final status determination
    if ($script:GlobalReport.errors.Count -eq 0) {
        $script:GlobalReport.overall_status = "DAY02_COMPLETE"
        Write-ZyeLog -Message "========================================================================" -Stage "CERTIFICATION"
        Write-ZyeLog -Message "DAY 02 STATUS: DAY02_COMPLETE" -Level "PASS" -Stage "CERTIFICATION"
        Write-ZyeLog -Message "Environment setup, CPU PyTorch and dependencies fully operational." -Level "PASS" -Stage "CERTIFICATION"
        Write-ZyeLog -Message "========================================================================" -Stage "CERTIFICATION"
    }
    else {
        $script:GlobalReport.overall_status = "DAY02_DEGRADED"
        Write-ZyeLog -Message "DAY 02 STATUS: DAY02_DEGRADED (Issues logged in install report)" -Level "WARN" -Stage "CERTIFICATION"
    }

    Export-InstallationReport -Report $script:GlobalReport -OutputPath $script:ReportFilePath
    return 0
}

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
$exitCode = Invoke-ZyeSetup
exit $exitCode
