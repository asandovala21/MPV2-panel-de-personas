#!/bin/bash
# =============================================================================
# SUBIR PARQUETS A AZURE BLOB STORAGE
# Sube TODOS los archivos parquet al blob storage, reemplazando los existentes
# Usar para actualizaciones de datos en produccion
# =============================================================================

set -e

RESOURCE_GROUP="panel-de-personas"
CONTAINER_NAME_BLOB="datos"

echo ""
echo "==========================================="
echo "SUBIR PARQUETS A AZURE BLOB STORAGE"
echo "==========================================="
echo ""

# Verificar login en Azure
echo "[1/3] Verificando sesion en Azure..."
if ! az account show > /dev/null 2>&1; then
    echo "No estas logueado. Ejecutando az login..."
    az login
fi
SUBSCRIPTION=$(az account show --query "name" -o tsv 2>/dev/null | tr -d '\r\n')
echo "   [OK] Conectado a: $SUBSCRIPTION"

# Obtener el nombre del storage account
echo "[2/3] Obteniendo Storage Account..."
STORAGE_ACCOUNT_NAME=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv 2>/dev/null | tr -d '\r\n')

if [ -z "$STORAGE_ACCOUNT_NAME" ]; then
    echo "[ERROR] No se encontro Storage Account en '$RESOURCE_GROUP'"
    exit 1
fi
echo "   [OK] Storage Account: $STORAGE_ACCOUNT_NAME"

# Subir todos los parquets
echo "[3/3] Subiendo TODOS los parquets (reemplazando existentes)..."
cd "$(dirname "$0")/.."

# Contar archivos
PARQUET_COUNT=$(ls -1 datos/parquet/*.parquet 2>/dev/null | wc -l)
echo "   Archivos encontrados: $PARQUET_COUNT"
echo ""

# Subir usando batch (mas eficiente)
az storage blob upload-batch \
    --account-name $STORAGE_ACCOUNT_NAME \
    --destination $CONTAINER_NAME_BLOB \
    --source datos/parquet \
    --pattern "*.parquet" \
    --auth-mode key \
    --overwrite \
    --only-show-errors

echo ""
echo "==========================================="
echo "[OK] SUBIDA COMPLETADA"
echo "==========================================="
echo ""
echo "Archivos subidos al contenedor '$CONTAINER_NAME_BLOB'"
echo "en Storage Account: $STORAGE_ACCOUNT_NAME"
echo ""
echo "Parquets actualizados:"
ls -1 datos/parquet/*.parquet 2>/dev/null | xargs -n1 basename
echo ""
