param(
  [int]$ServerPort = 9000,
  [string]$OutDir = $(Join-Path (Split-Path -Parent $PSScriptRoot) 'dumps'),
  [string]$ConfigPath = $(Join-Path $PSScriptRoot 'endoscope-telnet.local.ps1'),
  [int]$ExpectedBytes = 4194304
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

function New-TelnetSession {
  $client = [Net.Sockets.TcpClient]::new()
  $client.ReceiveTimeout = 2000
  $client.SendTimeout = 2000
  $client.Connect($EndoscopeTelnetHost, [int]$EndoscopeTelnetPort)
  $stream = $client.GetStream()
  $enc = [Text.Encoding]::ASCII

  $sendBytes = {
    param([byte[]]$Bytes)
    $stream.Write($Bytes, 0, $Bytes.Length)
    $stream.Flush()
  }

  $sendLine = {
    param([string]$Line)
    $bytes = $enc.GetBytes($Line + "`r`n")
    & $sendBytes $bytes
  }

  $readTelnet = {
    param([int]$TimeoutMs, [string[]]$Until)
    $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
    $sb = [Text.StringBuilder]::new()
    while ((Get-Date) -lt $deadline) {
      if (-not $stream.DataAvailable) {
        Start-Sleep -Milliseconds 30
        continue
      }
      $b = $stream.ReadByte()
      if ($b -lt 0) { break }

      if ($b -eq 255) {
        while (-not $stream.DataAvailable -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 10 }
        if (-not $stream.DataAvailable) { continue }
        $cmd = $stream.ReadByte()

        if ($cmd -eq 255) {
          [void]$sb.Append([char]255)
          continue
        }

        if ($cmd -in 251,252,253,254) {
          while (-not $stream.DataAvailable -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 10 }
          if ($stream.DataAvailable) {
            $opt = $stream.ReadByte()
            if ($cmd -eq 253) { & $sendBytes ([byte[]](255,252,$opt)) }
            elseif ($cmd -eq 251) { & $sendBytes ([byte[]](255,254,$opt)) }
          }
          continue
        }

        if ($cmd -eq 250) {
          $prev = -1
          while ((Get-Date) -lt $deadline) {
            if (-not $stream.DataAvailable) { Start-Sleep -Milliseconds 10; continue }
            $x = $stream.ReadByte()
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

  [pscustomobject]@{
    Client = $client
    Stream = $stream
    SendLine = $sendLine
    ReadTelnet = $readTelnet
  }
}

function Invoke-TelnetCommand([string]$Command, [int]$TimeoutMs = 10000) {
  $s = New-TelnetSession
  try {
    $null = & $s.ReadTelnet 5000 @('login:', 'Login:')
    & $s.SendLine $EndoscopeTelnetUser
    $null = & $s.ReadTelnet 5000 @('Password:', 'password:')
    & $s.SendLine $EndoscopeTelnetPassword
    $null = & $s.ReadTelnet 8000 @('# ', "#`r", "#`n", '$ ')
    & $s.SendLine $Command
    $out = & $s.ReadTelnet $TimeoutMs @('__END__')
    & $s.SendLine 'exit'
    $null = & $s.ReadTelnet 1000 @()
    if ($EndoscopeTelnetPassword) { $out = $out.Replace($EndoscopeTelnetPassword, '<password hidden>') }
    return $out
  } finally {
    try { $s.Stream.Close() } catch {}
    try { $s.Client.Close() } catch {}
  }
}

Log "Checking /proc/mtd and starting one-shot TCP sender on the endoscope"
$checkCmd = 'echo __BEGIN__; cat /proc/mtd; echo __END__'
$checkOut = Invoke-TelnetCommand $checkCmd 10000
$checkOut | Out-File -LiteralPath (Join-Path $OutDir "proc-mtd-$stamp.txt") -Encoding UTF8

$startCmd = "echo __BEGIN__; tcpsvd -c 1 0.0.0.0 $ServerPort cat /dev/mtd0 2>/tmp/mtd0-dump.err & echo __DUMP_SERVER_STARTED__; echo __END__"
$startOut = Invoke-TelnetCommand $startCmd 10000
$startOut | Out-File -LiteralPath (Join-Path $OutDir "tcp-sender-start-$stamp.txt") -Encoding UTF8

Start-Sleep -Milliseconds 500

Log "Connecting to $EndoscopeTelnetHost`:$ServerPort and receiving flash bytes"
$tcp = [Net.Sockets.TcpClient]::new()
$tcp.ReceiveTimeout = 15000
$tcp.SendTimeout = 5000
$tcp.Connect($EndoscopeTelnetHost, $ServerPort)
$ns = $tcp.GetStream()
$fs = [IO.File]::Open($outFile, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::Read)
$buf = New-Object byte[] 65536
$total = 0L
try {
  while ($total -lt $ExpectedBytes) {
    $n = $ns.Read($buf, 0, $buf.Length)
    if ($n -le 0) { break }
    $fs.Write($buf, 0, $n)
    $total += $n
  }
} finally {
  $fs.Close()
  $ns.Close()
  $tcp.Close()
}

Log "Received $total bytes"
if ($total -ne $ExpectedBytes) {
  throw "Unexpected dump size: $total bytes, expected $ExpectedBytes bytes"
}

$sha = (Get-FileHash -LiteralPath $outFile -Algorithm SHA256).Hash
Log "SHA256 flash_full_mtd0.bin $sha"

function Split-Part([string]$Name, [int64]$Offset, [int64]$Length) {
  $partPath = Join-Path $OutDir $Name
  $input = [IO.File]::OpenRead($outFile)
  $output = [IO.File]::Open($partPath, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::Read)
  try {
    $input.Position = $Offset
    $remaining = $Length
    $buffer = New-Object byte[] 65536
    while ($remaining -gt 0) {
      $want = [Math]::Min($buffer.Length, $remaining)
      $read = $input.Read($buffer, 0, [int]$want)
      if ($read -le 0) { throw "Unexpected EOF while splitting $Name" }
      $output.Write($buffer, 0, $read)
      $remaining -= $read
    }
  } finally {
    $output.Close()
    $input.Close()
  }
  [pscustomobject]@{
    File = $partPath
    Offset = $Offset
    Bytes = $Length
    SHA256 = (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash
  }
}

$parts = @(
  Split-Part 'mtd1_bootloader.bin' 0x000000 0x030000
  Split-Part 'mtd2_config.bin'     0x030000 0x010000
  Split-Part 'mtd3_factory.bin'    0x040000 0x010000
  Split-Part 'mtd4_kernel.bin'     0x050000 0x3B0000
)

$meta = [pscustomobject]@{
  Timestamp = $stamp
  Method = 'Wi-Fi Telnet starts one-shot tcpsvd sender; Windows receives raw /dev/mtd0 over TCP'
  Host = $EndoscopeTelnetHost
  Port = $ServerPort
  FullDump = [pscustomobject]@{
    File = $outFile
    Bytes = $total
    SHA256 = $sha
  }
  Parts = $parts
  Logs = @(
    $logFile,
    (Join-Path $OutDir "proc-mtd-$stamp.txt"),
    (Join-Path $OutDir "tcp-sender-start-$stamp.txt")
  )
}
$meta | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $metaFile -Encoding UTF8
Log "Metadata $metaFile"

$meta | ConvertTo-Json -Depth 6
