param(
  [int]$ServerPort = 9000,
  [string]$OutDir = '',
  [string]$ConfigPath = '',
  [int]$ExpectedBytes = 4194304
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $ProjectRoot 'dumps' }
if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'endoscope-telnet.local.ps1' }

if (-not (Test-Path -LiteralPath $ConfigPath)) {
  throw "Config file not found: $ConfigPath"
}
. $ConfigPath

if (-not $EndoscopeTelnetHost -or -not $EndoscopeTelnetPort -or -not $EndoscopeTelnetUser -or -not $EndoscopeTelnetPassword) {
  throw "Telnet config is incomplete: $ConfigPath"
}
if ($EndoscopeTelnetUser -eq '<LOGIN>' -or $EndoscopeTelnetPassword -eq '<PASSWORD>') {
  throw "Edit $ConfigPath first: replace placeholders."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outFile = Join-Path $OutDir 'flash_full_mtd0.bin'
$metaFile = Join-Path $OutDir "firmware-dump-$stamp.json"
$logFile = Join-Path $OutDir "firmware-dump-$stamp.log"

function Log([string]$Message) {
  $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
  Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
  Write-Host $line
}

function Send-TelnetBytes {
  param(
    [Parameter(Mandatory=$true)] [System.Net.Sockets.NetworkStream]$Stream,
    [Parameter(Mandatory=$true)] [byte[]]$Bytes
  )
  $Stream.Write($Bytes, 0, $Bytes.Length)
  $Stream.Flush()
}

function Send-TelnetLine {
  param(
    [Parameter(Mandatory=$true)] [System.Net.Sockets.NetworkStream]$Stream,
    [Parameter(Mandatory=$true)] [string]$Line
  )
  $encoding = [System.Text.Encoding]::ASCII
  $bytes = $encoding.GetBytes($Line + "`r`n")
  Send-TelnetBytes -Stream $Stream -Bytes $bytes
}

function Read-TelnetText {
  param(
    [Parameter(Mandatory=$true)] [System.Net.Sockets.NetworkStream]$Stream,
    [Parameter(Mandatory=$true)] [int]$TimeoutMs,
    [string[]]$Until = @()
  )

  $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
  $sb = [System.Text.StringBuilder]::new()

  while ((Get-Date) -lt $deadline) {
    if (-not $Stream.DataAvailable) {
      Start-Sleep -Milliseconds 30
      continue
    }

    $b = $Stream.ReadByte()
    if ($b -lt 0) { break }

    # Telnet IAC handling.
    if ($b -eq 255) {
      while (-not $Stream.DataAvailable -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 10 }
      if (-not $Stream.DataAvailable) { continue }
      $cmd = $Stream.ReadByte()

      if ($cmd -eq 255) {
        [void]$sb.Append([char]255)
        continue
      }

      # WILL/WONT/DO/DONT option negotiation.
      if ($cmd -in 251,252,253,254) {
        while (-not $Stream.DataAvailable -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 10 }
        if ($Stream.DataAvailable) {
          $opt = $Stream.ReadByte()
          if ($cmd -eq 253) {
            # Server asks us DO option -> WONT.
            Send-TelnetBytes -Stream $Stream -Bytes ([byte[]](255,252,$opt))
          } elseif ($cmd -eq 251) {
            # Server says WILL option -> DONT.
            Send-TelnetBytes -Stream $Stream -Bytes ([byte[]](255,254,$opt))
          }
        }
        continue
      }

      # SB ... SE subnegotiation.
      if ($cmd -eq 250) {
        $prev = -1
        while ((Get-Date) -lt $deadline) {
          if (-not $Stream.DataAvailable) { Start-Sleep -Milliseconds 10; continue }
          $x = $Stream.ReadByte()
          if ($prev -eq 255 -and $x -eq 240) { break }
          $prev = $x
        }
        continue
      }

      continue
    }

    if ($b -eq 0) { continue }
    [void]$sb.Append([char]$b)
    $txt = $sb.ToString()
    foreach ($u in $Until) {
      if ($u -and $txt.Contains($u)) { return $txt }
    }
  }

  return $sb.ToString()
}

function New-TelnetClient {
  $client = [System.Net.Sockets.TcpClient]::new()
  $client.ReceiveTimeout = 3000
  $client.SendTimeout = 3000
  $client.Connect($EndoscopeTelnetHost, [int]$EndoscopeTelnetPort)
  return $client
}

function Invoke-TelnetCommand {
  param(
    [Parameter(Mandatory=$true)] [string]$Command,
    [int]$TimeoutMs = 10000,
    [switch]$KeepOpen
  )

  $client = New-TelnetClient
  $stream = $client.GetStream()
  $closeSession = $true

  try {
    $loginText = Read-TelnetText -Stream $stream -TimeoutMs 6000 -Until @('login:', 'Login:')
    if ($loginText -notmatch '(?i)login:') {
      throw "Did not receive Telnet login prompt. Received: $loginText"
    }

    Send-TelnetLine -Stream $stream -Line $EndoscopeTelnetUser

    $passwordText = Read-TelnetText -Stream $stream -TimeoutMs 6000 -Until @('Password:', 'password:')
    if ($passwordText -notmatch '(?i)password:') {
      throw "Did not receive Telnet password prompt."
    }

    Send-TelnetLine -Stream $stream -Line $EndoscopeTelnetPassword

    $promptText = Read-TelnetText -Stream $stream -TimeoutMs 8000 -Until @('# ', "#`r", "#`n", '$ ')
    if ($promptText -notmatch '#|\$') {
      throw "Did not receive shell prompt after login."
    }

    # Disable terminal echo so command text is not confused with output markers.
    Send-TelnetLine -Stream $stream -Line 'stty -echo 2>/dev/null'
    $null = Read-TelnetText -Stream $stream -TimeoutMs 2000 -Until @('# ', "#`r", "#`n", '$ ')

    if ($KeepOpen) {
      # Foreground commands such as tcpsvd need the Telnet shell to stay alive while another TCP client connects.
      Send-TelnetLine -Stream $stream -Line $Command
      $closeSession = $false

      return [pscustomobject]@{
        Client = $client
        Stream = $stream
      }
    }

    # Do not put literal __END__ into the command line: the device echoes typed commands.
    # Print markers via octal escapes so only real command output contains them.
    $wrapped = "printf '\137\137BEGIN\137\137\012'; $Command; printf '\137\137END\137\137\012'"
    Send-TelnetLine -Stream $stream -Line $wrapped
    $out = Read-TelnetText -Stream $stream -TimeoutMs $TimeoutMs -Until @('__END__')

    Send-TelnetLine -Stream $stream -Line 'exit'
    $null = Read-TelnetText -Stream $stream -TimeoutMs 1000 -Until @()

    if ($EndoscopeTelnetPassword) { $out = $out.Replace($EndoscopeTelnetPassword, '<password hidden>') }
    return $out
  }
  finally {
    if ($closeSession) {
      try { $stream.Close() } catch {}
      try { $client.Close() } catch {}
    }
  }
}

function Connect-WithRetry {
  param(
    [Parameter(Mandatory=$true)] [string]$HostName,
    [Parameter(Mandatory=$true)] [int]$Port,
    [int]$Attempts = 20,
    [int]$DelayMs = 250
  )

  $lastError = $null
  for ($i = 1; $i -le $Attempts; $i++) {
    try {
      $tcp = [System.Net.Sockets.TcpClient]::new()
      $tcp.ReceiveTimeout = 15000
      $tcp.SendTimeout = 5000
      $ar = $tcp.BeginConnect($HostName, $Port, $null, $null)
      if (-not $ar.AsyncWaitHandle.WaitOne(1000, $false)) {
        try { $tcp.Close() } catch {}
        throw 'connect timeout'
      }
      $tcp.EndConnect($ar)
      return $tcp
    } catch {
      $lastError = $_.Exception.Message
      Start-Sleep -Milliseconds $DelayMs
    }
  }
  throw "Could not connect to $HostName`:$Port after $Attempts attempts. Last error: $lastError"
}

function Split-Part {
  param(
    [Parameter(Mandatory=$true)] [string]$Name,
    [Parameter(Mandatory=$true)] [int64]$Offset,
    [Parameter(Mandatory=$true)] [int64]$Length
  )

  $partPath = Join-Path $OutDir $Name
  $inputFile = [System.IO.File]::OpenRead($outFile)
  $outputFile = [System.IO.File]::Open($partPath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
  try {
    $inputFile.Position = $Offset
    $remaining = $Length
    $buffer = New-Object byte[] 65536
    while ($remaining -gt 0) {
      $want = [Math]::Min($buffer.Length, $remaining)
      $read = $inputFile.Read($buffer, 0, [int]$want)
      if ($read -le 0) { throw "Unexpected EOF while splitting $Name" }
      $outputFile.Write($buffer, 0, $read)
      $remaining -= $read
    }
  }
  finally {
    $outputFile.Close()
    $inputFile.Close()
  }

  [pscustomobject]@{
    Path = $partPath
    Offset = ('0x{0:X6}' -f $Offset)
    OffsetBytes = $Offset
    Size = ('0x{0:X6}' -f $Length)
    Bytes = $Length
    SHA256 = (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash
  }
}

Log "Running read-only Telnet diagnostics"
$checkOut = Invoke-TelnetCommand -Command 'cat /proc/mtd' -TimeoutMs 10000
$devMtdOut = Invoke-TelnetCommand -Command 'ls -l /dev/mtd*' -TimeoutMs 10000
$devMtdBlockOut = Invoke-TelnetCommand -Command 'ls -l /dev/mtdblock*' -TimeoutMs 10000
$whichTcpsvdOut = Invoke-TelnetCommand -Command 'which tcpsvd' -TimeoutMs 10000
$whichNcOut = Invoke-TelnetCommand -Command 'which nc' -TimeoutMs 10000
$whichDdOut = Invoke-TelnetCommand -Command 'which dd' -TimeoutMs 10000
$busyboxOut = Invoke-TelnetCommand -Command 'busybox' -TimeoutMs 10000

$checkFile = Join-Path $OutDir "firmware-diagnostics-$stamp.txt"
@(
  '=== cat /proc/mtd ==='
  $checkOut
  ''
  '=== ls -l /dev/mtd* ==='
  $devMtdOut
  ''
  '=== ls -l /dev/mtdblock* ==='
  $devMtdBlockOut
  ''
  '=== which tcpsvd ==='
  $whichTcpsvdOut
  ''
  '=== which nc ==='
  $whichNcOut
  ''
  '=== which dd ==='
  $whichDdOut
  ''
  '=== busybox ==='
  $busyboxOut
) | Out-File -LiteralPath $checkFile -Encoding UTF8

if ($checkOut -notlike '*mtd0: 00400000 00010000 "ALL"*') {
  throw "Unexpected mtd0 layout. See: $checkFile"
}
if ($busyboxOut -notmatch '(?m)\btcpsvd\b') {
  throw "BusyBox tcpsvd applet is not available. See: $checkFile"
}

Log "Starting foreground TCP sender for /dev/mtd0 while keeping Telnet open"
$startCmd = "busybox tcpsvd -c 1 $EndoscopeTelnetHost $ServerPort cat /dev/mtd0"
$startFile = Join-Path $OutDir "tcp-sender-start-$stamp.txt"
$startCmd | Out-File -LiteralPath $startFile -Encoding UTF8
$senderSession = Invoke-TelnetCommand -Command $startCmd -KeepOpen

Start-Sleep -Milliseconds 300

$partialFile = "$outFile.partial"
if (Test-Path -LiteralPath $partialFile) {
  Remove-Item -LiteralPath $partialFile -Force
}

Log "Connecting to $EndoscopeTelnetHost`:$ServerPort and receiving flash bytes"
$tcp = $null
$ns = $null
$fs = $null
$total = 0L

try {
  $tcp = Connect-WithRetry -HostName $EndoscopeTelnetHost -Port $ServerPort
  $ns = $tcp.GetStream()
  $fs = [System.IO.File]::Open($partialFile, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
  $buf = New-Object byte[] 65536

  while ($total -lt $ExpectedBytes) {
    $want = [Math]::Min($buf.Length, $ExpectedBytes - $total)
    $n = $ns.Read($buf, 0, [int]$want)
    if ($n -le 0) { break }
    $fs.Write($buf, 0, $n)
    $total += $n

    if (($total % 1048576) -lt $n) {
      Log "Received $total bytes"
    }
  }
}
finally {
  if ($fs) { try { $fs.Close() } catch {} }
  if ($ns) { try { $ns.Close() } catch {} }
  if ($tcp) { try { $tcp.Close() } catch {} }

  if ($senderSession) {
    try { Send-TelnetBytes -Stream $senderSession.Stream -Bytes ([byte[]](3)) } catch {}
    try { $null = Read-TelnetText -Stream $senderSession.Stream -TimeoutMs 1000 -Until @('# ', "#`r", "#`n", '$ ') } catch {}
    try { $senderSession.Stream.Close() } catch {}
    try { $senderSession.Client.Close() } catch {}
  }
}

Log "Received total $total bytes"
if ($total -ne $ExpectedBytes) {
  throw "Unexpected dump size: $total bytes, expected $ExpectedBytes bytes. Partial file: $partialFile"
}

$actualBytes = (Get-Item -LiteralPath $partialFile).Length
if ($actualBytes -ne $ExpectedBytes) {
  throw "Unexpected dump file size: $actualBytes bytes, expected $ExpectedBytes bytes"
}

Move-Item -LiteralPath $partialFile -Destination $outFile -Force

$sha = (Get-FileHash -LiteralPath $outFile -Algorithm SHA256).Hash
Log "SHA256 flash_full_mtd0.bin $sha"

$parts = @(
  Split-Part -Name 'mtd1_bootloader.bin' -Offset 0x000000 -Length 0x030000
  Split-Part -Name 'mtd2_config.bin'     -Offset 0x030000 -Length 0x010000
  Split-Part -Name 'mtd3_factory.bin'    -Offset 0x040000 -Length 0x010000
  Split-Part -Name 'mtd4_kernel.bin'     -Offset 0x050000 -Length 0x3B0000
)

$meta = [pscustomobject]@{
  Timestamp = (Get-Date).ToString('o')
  Method = 'Wi-Fi Telnet + TCP raw /dev/mtd0'
  Host = $EndoscopeTelnetHost
  Port = $ServerPort
  FullDump = [pscustomobject]@{
    Path = $outFile
    Bytes = $total
    SHA256 = $sha
  }
  Parts = $parts
  Logs = @($logFile, $checkFile, $startFile)
}
$meta | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $metaFile -Encoding UTF8
Log "Metadata $metaFile"

$meta | ConvertTo-Json -Depth 6
