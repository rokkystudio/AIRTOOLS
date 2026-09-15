param(
  [Parameter(Mandatory=$true)]
  [string[]]$Command,

  [int]$TimeoutSec = 20,

  [string]$ConfigPath = $(Join-Path $PSScriptRoot 'endoscope-telnet.local.ps1')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ConfigPath)) {
  throw "Config file not found: $ConfigPath"
}

. $ConfigPath

if (-not $EndoscopeTelnetHost -or -not $EndoscopeTelnetPort -or -not $EndoscopeTelnetUser -or -not $EndoscopeTelnetPassword) {
  throw "Telnet config is incomplete: $ConfigPath"
}
if ($EndoscopeTelnetUser -eq '<LOGIN>' -or $EndoscopeTelnetPassword -eq '<PASSWORD>') {
  throw "Edit $ConfigPath first: replace <LOGIN> and <PASSWORD>."
}

function Resolve-Plink {
  $candidates = @(
    (Join-Path $PSScriptRoot '..\tools\plink.exe'),
    (Join-Path $PSScriptRoot '..\tools\PuTTY\plink.exe'),
    (Join-Path $PSScriptRoot '..\tools\putty\plink.exe'),
    "$env:ProgramFiles\PuTTY\plink.exe",
    "${env:ProgramFiles(x86)}\PuTTY\plink.exe"
  )

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
      return (Resolve-Path -LiteralPath $candidate).Path
    }
  }

  $cmd = Get-Command plink.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  throw "plink.exe not found. Install PuTTY or put plink.exe into tools\."
}

$plink = Resolve-Plink
$cmdText = ($Command -join ' ')

$stdinLines = @(
  $EndoscopeTelnetUser,
  $EndoscopeTelnetPassword,
  $cmdText,
  'exit'
)
$stdinText = ($stdinLines -join "`r`n") + "`r`n"

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $plink
$psi.Arguments = "-telnet $EndoscopeTelnetHost $EndoscopeTelnetPort"
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$p = [System.Diagnostics.Process]::new()
$p.StartInfo = $psi
[void]$p.Start()
$p.StandardInput.Write($stdinText)
$p.StandardInput.Close()

if (-not $p.WaitForExit($TimeoutSec * 1000)) {
  try { $p.Kill() } catch {}
  throw "Telnet command timed out after $TimeoutSec seconds."
}

$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()

# Never print the local password even if the target echoes it.
if ($EndoscopeTelnetPassword) {
  $out = $out.Replace($EndoscopeTelnetPassword, '<password hidden>')
  $err = $err.Replace($EndoscopeTelnetPassword, '<password hidden>')
}

if ($out) { Write-Output $out }
if ($err) { Write-Error $err }
exit $p.ExitCode