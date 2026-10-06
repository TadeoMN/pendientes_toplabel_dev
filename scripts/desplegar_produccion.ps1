<#
Prepara o aplica BD y código. Sin -Aplicar solo diagnostica y compara archivos.
Requiere PowerShell y el Python del venv de desarrollo. No administra servicios.
#>
[CmdletBinding()]
param(
    [string]$Desarrollo = 'C:\sites\pendientes_toplabel_dev',
    [string]$Produccion = 'C:\sites\pendientes_toplabel',
    [string]$BaseDatos = 'toplabel_pendientes_prod',
    [ValidateSet('multipilares', 'reportes', 'roles_archivos', 'notas_estatus')]
    [string]$Hasta = 'notas_estatus',
    [string]$AdministradorInicial,
    [string]$DirectorioInformes,
    [switch]$Aplicar,
    [switch]$MantenimientoConfirmado
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$devRoot = (Resolve-Path -LiteralPath $Desarrollo).Path.TrimEnd('\')
$prodRoot = (Resolve-Path -LiteralPath $Produccion).Path.TrimEnd('\')
if ($devRoot -eq $prodRoot) { throw 'Desarrollo y producción deben ser carpetas diferentes.' }
if ($Aplicar -and -not $MantenimientoConfirmado) {
    throw 'Detén los escritores y vuelve a ejecutar con -Aplicar -MantenimientoConfirmado.'
}
if (-not $Aplicar -and $MantenimientoConfirmado) { throw 'La confirmación de mantenimiento se usa con -Aplicar.' }
if ($Hasta -ne 'notas_estatus') { throw 'Esta versión del código requiere -Hasta notas_estatus.' }
$sourceApp = Join-Path $devRoot 'app'
$targetApp = Join-Path $prodRoot 'app'
$targetEnv = Join-Path $prodRoot '.env'
$python = Join-Path $devRoot 'venv\Scripts\python.exe'
$migration = Join-Path $devRoot 'scripts\migraciones_produccion.py'
foreach ($requiredPath in @($sourceApp, $targetApp, $targetEnv, $python, $migration)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Falta la ruta requerida: $requiredPath" }
}
foreach ($tree in @($sourceApp, $targetApp)) {
    $items = @((Get-Item -LiteralPath $tree)) + @(Get-ChildItem -LiteralPath $tree -Recurse -Force)
    if ($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
        throw 'La publicación no admite enlaces/junctions dentro de app.'
    }
}

$changes = @()
foreach ($file in Get-ChildItem -LiteralPath $sourceApp -Recurse -File) {
    $relative = $file.FullName.Substring($sourceApp.Length + 1)
    if ($relative -match '(^|[\\/])__pycache__([\\/]|$)' -or $file.Extension -in @('.pyc', '.pyo') -or $relative -eq 'config.py') { continue }
    $destination = [IO.Path]::GetFullPath((Join-Path $targetApp $relative))
    if (-not $destination.StartsWith($targetApp + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Se detectó una ruta fuera de la carpeta app de destino.'
    }
    $newHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    $oldHash = if (Test-Path -LiteralPath $destination) { (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash } else { $null }
    if ($oldHash -ne $newHash) {
        $changes += [ordered]@{ relative = $relative; source = $file.FullName; target = $destination; before = $oldHash; after = $newHash }
    }
}
Write-Output ("Destino de código: " + $prodRoot)
Write-Output ("Archivos por actualizar: " + $changes.Count)
foreach ($change in $changes) { Write-Output ("  app\" + $change.relative) }

$outputRoot = if ($DirectorioInformes) { $DirectorioInformes } else { 'C:\sites\migraciones_pendientes\revision_migracion\publicaciones' }
$migrationArgs = @($migration, '--env-file', $targetEnv, '--database', $BaseDatos, '--output-dir', $outputRoot, '--hasta', $Hasta)
if ($AdministradorInicial) { $migrationArgs += @('--admin-usuario', $AdministradorInicial) }
Push-Location -LiteralPath $devRoot
try {
    & $python -B -c 'import sys; from scripts.migracion_acceso import carpeta_adjuntos; assert carpeta_adjuntos(sys.argv[1],sys.argv[2]) != carpeta_adjuntos(sys.argv[3],sys.argv[4]), "Desarrollo y producción comparten adjuntos"' $targetEnv $BaseDatos (Join-Path $devRoot '.env') 'toplabel_pendientes'
    if ($LASTEXITCODE -ne 0) { throw 'Desarrollo y producción deben usar almacenamiento de adjuntos separado.' }
    # La migración respalda y verifica BD y adjuntos en una misma carpeta de ejecución.
    if (-not $Aplicar) {
        & $python -B @migrationArgs --dry-run
        if ($LASTEXITCODE -ne 0) { throw 'El diagnóstico de BD falló. Revisar el informe antes de publicar.' }
        Write-Output 'Diagnóstico terminado. Para aplicar se requiere mantenimiento y los dos switches de confirmación.'
        return
    }

    $runRoot = Join-Path $outputRoot ('codigo_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8))
    & $python -B -c 'import sys; from scripts.migracion_estructura import private_directory, validate_output_dir; private_directory(validate_output_dir(sys.argv[1]))' $runRoot
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la carpeta privada de respaldo.' }
    $backup = Join-Path $runRoot 'app_antes.zip'
    Compress-Archive -LiteralPath $targetApp -DestinationPath $backup
    if ((Get-Item -LiteralPath $backup).Length -eq 0) { throw 'El respaldo de código está vacío.' }
    # Comprobar que el ZIP se puede leer antes de modificar la BD.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($backup)
    try {
        if ($zip.Entries.Count -eq 0) { throw 'El respaldo de código no contiene archivos.' }
        foreach ($entry in $zip.Entries) {
            $entryStream = $entry.Open()
            try { $entryStream.CopyTo([IO.Stream]::Null) } finally { $entryStream.Dispose() }
        }
    } finally { $zip.Dispose() }
    $manifest = [ordered]@{
        database = $BaseDatos; target = $prodRoot; schema_target = $Hasta; status = 'codigo_respaldado';
        backup = $backup; backup_sha256 = (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash;
        files = $changes; copied = @(); maintenance_required = $true
    }
    $manifestPath = Join-Path $runRoot 'publicacion.json'
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
    try {
        & $python -B @migrationArgs --apply --confirm-database $BaseDatos --maintenance-confirmed
        if ($LASTEXITCODE -ne 0) { throw 'La migración falló. El código no se copió; revisar DDL parcial e informe.' }
        # Detectar cambios concurrentes de archivos después de preparar el plan.
        foreach ($change in $changes) {
            $currentHash = if (Test-Path -LiteralPath $change.target) { (Get-FileHash -LiteralPath $change.target -Algorithm SHA256).Hash } else { $null }
            if ($currentHash -ne $change.before -or (Get-FileHash -LiteralPath $change.source -Algorithm SHA256).Hash -ne $change.after) {
                throw 'El código cambió durante la preparación. Mantener mantenimiento y revisar antes de continuar.'
            }
        }
        foreach ($change in $changes) {
            $parent = Split-Path -Parent $change.target
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
            Copy-Item -LiteralPath $change.source -Destination $change.target -Force
            if ((Get-FileHash -LiteralPath $change.target -Algorithm SHA256).Hash -ne $change.after) {
                throw ('No se verificó el archivo ' + $change.relative)
            }
            $manifest.copied += $change.relative
            $manifest.status = 'copiando_codigo'
            $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
        }
        $manifest.status = 'codigo_verificado'
        Write-Output 'BD y archivos verificados. Reinicia el proceso de la aplicación y valida antes de reabrir escrituras.'
    } catch {
        $manifest.status = 'fallo_requiere_revision'
        throw
    } finally {
        $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
        Write-Output ("Respaldo y registro de código: " + $runRoot)
    }
} finally {
    Pop-Location
}
