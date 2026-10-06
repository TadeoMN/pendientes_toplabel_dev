<#
Migraciones versionadas de BD, sin copiar código ni importar datos.
Sin -Aplicar solo diagnostica. El mantenimiento se realiza fuera de este script.
#>
[CmdletBinding()]
param(
    [string]$Desarrollo = (Split-Path -Parent $PSScriptRoot),
    [string]$Produccion = 'C:\sites\pendientes_toplabel',
    [string]$BaseDatos = 'toplabel_pendientes_prod',
    [ValidateSet('multipilares', 'reportes', 'roles_archivos', 'notas_estatus')]
    [string]$Hasta = 'notas_estatus',
    [string]$AdministradorInicial,
    [string]$Mysqldump = 'C:\Program Files\MySQL\MySQL Server 9.5\bin\mysqldump.exe',
    [string]$DirectorioInformes,
    [switch]$Aplicar,
    [switch]$MantenimientoConfirmado
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($Aplicar -and -not $MantenimientoConfirmado) {
    throw 'Detén todos los escritores del destino y usa -Aplicar -MantenimientoConfirmado.'
}
if (-not $Aplicar -and $MantenimientoConfirmado) {
    throw 'La confirmación de mantenimiento solo se usa con -Aplicar.'
}
$devRoot = (Resolve-Path -LiteralPath $Desarrollo).Path.TrimEnd('\')
$prodRoot = (Resolve-Path -LiteralPath $Produccion).Path.TrimEnd('\')
if ($devRoot -eq $prodRoot) { throw 'Desarrollo y destino deben ser carpetas diferentes.' }
$python = Join-Path $devRoot 'venv\Scripts\python.exe'
$migration = Join-Path $devRoot 'scripts\migraciones_produccion.py'
$targetEnv = Join-Path $prodRoot '.env'
foreach ($requiredPath in @($python, $migration, $targetEnv)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Falta el archivo requerido: $requiredPath"
    }
}
$outputRoot = if ($DirectorioInformes) { $DirectorioInformes } else { 'C:\sites\migraciones_pendientes\revision_migracion\publicaciones' }
$migrationArgs = @($migration, '--env-file', $targetEnv, '--database', $BaseDatos,
                   '--output-dir', $outputRoot, '--hasta', $Hasta, '--mysqldump', $Mysqldump)
if ($AdministradorInicial) { $migrationArgs += @('--admin-usuario', $AdministradorInicial) }
if ($Aplicar) {
    $migrationArgs += @('--apply', '--confirm-database', $BaseDatos, '--maintenance-confirmed')
} else {
    $migrationArgs += '--dry-run'
}
Write-Output ("Destino de BD: " + $BaseDatos + "; versión solicitada: " + $Hasta)
& $python -B @migrationArgs
if ($LASTEXITCODE -ne 0) {
    throw 'La migración no terminó correctamente. Revisa el informe y conserva el mantenimiento si se inició DDL.'
}
if ($Aplicar) {
    Write-Output 'Estructura y conservación de datos verificadas. Valida la aplicación antes de reabrir escrituras.'
} else {
    Write-Output 'Diagnóstico terminado. Para aplicar, detén escritores y usa -Aplicar -MantenimientoConfirmado.'
}
