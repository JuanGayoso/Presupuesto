# Asistente de primer arranque (Windows PowerShell): pide la configuración y crea el archivo .env.
# Uso:  .\setup.ps1     (si PowerShell bloquea scripts: powershell -ExecutionPolicy Bypass -File .\setup.ps1)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (Test-Path .env) {
  $ans = Read-Host "Ya existe un archivo .env. ¿Sobrescribirlo? [s/N]"
  if ($ans -notmatch '^[sSyY]$') { Write-Host "Sin cambios."; exit 0 }
}

function Ask($prompt, $default) {
  $v = Read-Host "$prompt [$default]"
  if ([string]::IsNullOrWhiteSpace($v)) { return $default } else { return $v }
}

Write-Host "== Configuración de Evaluación Inmobiliaria =="
Write-Host "(Enter acepta el valor entre corchetes)"

$db = Ask "Nombre de la base de datos" "evaluacion_inmobiliaria"
$user = Ask "Usuario de la base de datos" "evaluacion"

while ($true) {
  $secure = Read-Host "Contraseña de la base de datos (Enter = generar una segura)" -AsSecureString
  $pass = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
  if ([string]::IsNullOrEmpty($pass)) {
    $bytes = New-Object byte[] 16
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $pass = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    Write-Host "Contraseña generada y guardada en .env"
    break
  }
  if ($pass -match '^[A-Za-z0-9_.-]+$') { break }
  Write-Host "Usa solo letras, números, '_', '.' o '-'."
}

$port = Ask "Puerto de la aplicación" "8000"
$demo = Read-Host "¿Crear la plantilla demo en el primer arranque? [S/n]"
$seed = if ($demo -match '^[nN]$') { "false" } else { "true" }

$content = "POSTGRES_USER=$user`nPOSTGRES_DB=$db`nPOSTGRES_PASSWORD=$pass`nAPP_PORT=$port`nSEED_ON_STARTUP=$seed`n"
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ".env"), $content)
Write-Host "`nArchivo .env creado."

$go = Read-Host "¿Levantar la aplicación ahora con Docker? [S/n]"
if ($go -notmatch '^[nN]$') {
  docker compose up --build -d
  Write-Host "Listo: http://localhost:$port"
} else {
  Write-Host "Cuando quieras: docker compose up --build -d"
}
