<#
    Levanta todo el sistema de Control de Acceso de una sola vez:
      1. Backend (FastAPI)   -> ventana nueva, http://127.0.0.1:8000
      2. Frontend (React)    -> ventana nueva, http://localhost:5173
                                 (se omite si no hay Node/npm instalado)
      3. Terminal de QR      -> en esta misma ventana (abre la cámara)

    La primera vez crea los entornos virtuales que falten e instala
    dependencias, así que puede tardar un par de minutos. Las
    siguientes veces es mucho más rápido.

    Uso:
        clic derecho sobre este archivo -> "Ejecutar con PowerShell"

    o desde una terminal PowerShell, parado en esta carpeta:
        powershell -ExecutionPolicy Bypass -File .\iniciar.ps1
#>

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot

function Escribir-Titulo($texto) {
    Write-Host ""
    Write-Host "==== $texto ====" -ForegroundColor Cyan
}

function Buscar-Python {
    foreach ($candidato in @("python", "py")) {
        if (Get-Command $candidato -ErrorAction SilentlyContinue) {
            return $candidato
        }
    }
    throw "No se encontró Python en el PATH. Instala Python 3.11+ (python.org) y vuelve a intentar."
}

# ------------------------------------------------------------------
# 1. Backend
# ------------------------------------------------------------------
Escribir-Titulo "Backend"

$backendDir = Join-Path $raiz "backend"
$backendVenv = Join-Path $backendDir ".venv"
$backendPython = Join-Path $backendVenv "Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    Write-Host "No existe el entorno virtual del backend, creándolo..."
    $py = Buscar-Python
    & $py -m venv $backendVenv
}

Write-Host "Revisando dependencias del backend (si falta alguna, se instala)..."
& $backendPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $backendDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "No se pudieron instalar las dependencias del backend (ver el error de pip" -ForegroundColor Red
    Write-Host "arriba). Nada más va a funcionar hasta que esto pase, así que me detengo aquí." -ForegroundColor Red
    exit 1
}

$backendEnv = Join-Path $backendDir ".env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $backendDir ".env.example") $backendEnv
    Write-Host "Se creó backend\.env a partir de .env.example." -ForegroundColor Yellow
    Write-Host "Revisa DATABASE_URL ahí si tu PostgreSQL usa otro usuario/contraseña." -ForegroundColor Yellow
}

Write-Host "Creando usuario admin y punto de acceso inicial (si no existen)..."
& $backendPython (Join-Path $backendDir "seed_db.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "seed_db.py terminó con errores — probablemente PostgreSQL no está" -ForegroundColor Yellow
    Write-Host "corriendo o backend\.env tiene mal la conexión. Revisa eso; el script" -ForegroundColor Yellow
    Write-Host "sigue de todas formas, pero el backend probablemente tampoco arranque." -ForegroundColor Yellow
}

Write-Host "Levantando el backend en una ventana nueva (http://127.0.0.1:8000)..."
$cmdBackend = "& `"$backendPython`" -m uvicorn app.main:app --reload"
Start-Process powershell -WorkingDirectory $backendDir -ArgumentList "-NoExit", "-Command", $cmdBackend

# ------------------------------------------------------------------
# 2. Frontend (opcional, solo si hay Node/npm instalado)
# ------------------------------------------------------------------
Escribir-Titulo "Frontend"

$frontendDir = Join-Path $raiz "frontend"

if (Get-Command npm -ErrorAction SilentlyContinue) {
    $nodeModules = Join-Path $frontendDir "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "Instalando dependencias del frontend (npm install, puede tardar)..."
        Push-Location $frontendDir
        npm install
        Pop-Location
    }

    $frontendEnv = Join-Path $frontendDir ".env"
    if (-not (Test-Path $frontendEnv)) {
        Copy-Item (Join-Path $frontendDir ".env.example") $frontendEnv
    }

    Write-Host "Levantando el frontend en una ventana nueva (http://localhost:5173)..."
    Start-Process powershell -WorkingDirectory $frontendDir -ArgumentList "-NoExit", "-Command", "npm run dev"
} else {
    Write-Host "No se encontró 'npm' en el PATH — se omite el frontend." -ForegroundColor Yellow
    Write-Host "Instala Node.js (nodejs.org) si también lo quieres levantar." -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# 3. Terminal de lectura de QR (en esta misma ventana)
# ------------------------------------------------------------------
Escribir-Titulo "Terminal QR"

$terminalDir = Join-Path $raiz "terminal"
$terminalVenv = Join-Path $terminalDir ".venv"
$terminalPython = Join-Path $terminalVenv "Scripts\python.exe"

if (-not (Test-Path $terminalPython)) {
    Write-Host "No existe el entorno virtual del terminal, creándolo..."
    $py = Buscar-Python
    & $py -m venv $terminalVenv
}

Write-Host "Revisando dependencias del terminal (si falta alguna, se instala)..."
& $terminalPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $terminalDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "No se pudieron instalar las dependencias del terminal (ver el error de pip" -ForegroundColor Red
    Write-Host "arriba). El backend (y el frontend, si se abrió) ya quedaron corriendo en" -ForegroundColor Red
    Write-Host "sus ventanas, pero no puedo abrir la cámara hasta resolver esto." -ForegroundColor Red
    exit 1
}

$terminalEnv = Join-Path $terminalDir ".env"
if (-not (Test-Path $terminalEnv)) {
    Copy-Item (Join-Path $terminalDir ".env.example") $terminalEnv
}

Write-Host ""
Write-Host "Esperando unos segundos a que el backend termine de levantar..."
Start-Sleep -Seconds 4

Write-Host "Abriendo la cámara. Muestra tu código QR. ESC para salir." -ForegroundColor Green
Push-Location $terminalDir
& $terminalPython "leer_qr.py"
Pop-Location

Write-Host ""
Write-Host "Terminal QR cerrado." -ForegroundColor Cyan
Write-Host "El backend (y el frontend, si se abrió) siguen corriendo en sus propias" -ForegroundColor Cyan
Write-Host "ventanas — ciérralas manualmente cuando termines." -ForegroundColor Cyan
