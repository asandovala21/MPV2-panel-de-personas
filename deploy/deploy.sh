#!/bin/bash
# =============================================================================
# DEPLOY PANEL DE PERSONAS - Azure Container Apps
# Construcción en la nube (sin Docker local)
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
RESOURCE_GROUP="panel-de-personas"
CONTAINER_APP_NAME="panel-app"
IMAGE_TAG="v$(date +%Y%m%d%H%M%S)"

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🚀 DEPLOY PANEL DE PERSONAS - AZURE${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# =============================================================================
# 1. VERIFICAR SESIÓN EN AZURE
# =============================================================================
echo -e "${YELLOW}[1/5]${NC} Verificando sesión en Azure..."

if ! az account show > /dev/null 2>&1; then
    echo -e "${RED}No estás logueado. Ejecutando az login...${NC}"
    az login
fi

SUBSCRIPTION=$(az account show --query "name" -o tsv 2>/dev/null | tr -d '\r\n')
echo -e "   ${GREEN}✓${NC} Conectado a: $SUBSCRIPTION"
echo ""

# =============================================================================
# 2. OBTENER CONFIGURACIÓN DE AZURE
# =============================================================================
echo -e "${YELLOW}[2/5]${NC} Obteniendo configuración de Azure..."

ACR_NAME=$(az acr list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv 2>/dev/null | tr -d '\r\n')

if [ -z "$ACR_NAME" ]; then
    echo -e "${RED}Error: No se encontró ACR en '$RESOURCE_GROUP'${NC}"
    echo "Ejecuta primero: ./setup_azure.sh"
    exit 1
fi

IMAGE_FULL="$ACR_NAME.azurecr.io/panel-personas:$IMAGE_TAG"
echo -e "   ${GREEN}✓${NC} ACR: $ACR_NAME"
echo -e "   ${GREEN}✓${NC} Imagen: panel-personas:$IMAGE_TAG"
echo ""

# =============================================================================
# 3. PREPARAR ARCHIVOS
# =============================================================================
echo -e "${YELLOW}[3/5]${NC} Preparando archivos para el build..."

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

# Crear directorio temporal limpio
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copiar solo lo necesario
cp -r backend "$TEMP_DIR/"
cp -r frontend "$TEMP_DIR/"
cp main.py "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/"
cp Dockerfile "$TEMP_DIR/"

echo -e "   ${GREEN}✓${NC} Archivos preparados en: $TEMP_DIR"
echo ""

# =============================================================================
# 4. CONSTRUIR EN AZURE
# =============================================================================
echo -e "${YELLOW}[4/5]${NC} Construyendo imagen en Azure..."
echo "   Esto puede tomar 2-3 minutos..."
echo ""

cd "$TEMP_DIR"

# Iniciar build sin esperar (evita problemas de codificación en Windows)
az acr build \
    --registry "$ACR_NAME" \
    --image "panel-personas:$IMAGE_TAG" \
    --image "panel-personas:latest" \
    --file Dockerfile \
    . \
    --no-wait \
    --only-show-errors

sleep 3

# Obtener ID del build más reciente
BUILD_ID=$(az acr task list-runs --registry "$ACR_NAME" --top 1 --query "[0].runId" -o tsv 2>/dev/null | tr -d '\r\n')
echo -e "   Build ID: ${BLUE}$BUILD_ID${NC}"

# Esperar a que termine
echo -e "   Esperando finalización..."
MAX_WAIT=120
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    STATUS=$(az acr task list-runs --registry "$ACR_NAME" --top 1 --query "[0].status" -o tsv 2>/dev/null | tr -d '\r\n')
    
    if [ "$STATUS" = "Succeeded" ]; then
        echo -e "   ${GREEN}✓${NC} Build completado exitosamente"
        break
    elif [ "$STATUS" = "Failed" ] || [ "$STATUS" = "Error" ]; then
        echo -e "   ${RED}✗${NC} Build falló. Ver logs en Azure Portal"
        exit 1
    fi
    
    sleep 10
    WAIT_TIME=$((WAIT_TIME + 10))
    echo -e "   Estado: $STATUS (${WAIT_TIME}s)"
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "   ${YELLOW}⚠${NC} Timeout esperando build. Continuando..."
fi

echo ""

# =============================================================================
# 5. ACTUALIZAR CONTAINER APP
# =============================================================================
echo -e "${YELLOW}[5/5]${NC} Actualizando Container App..."

az containerapp update \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$IMAGE_FULL" \
    --set-env-vars "DEPLOY_VERSION=$IMAGE_TAG" \
    --only-show-errors \
    --output none

echo -e "   ${GREEN}✓${NC} Container App actualizada"
echo ""

# Esperar inicio
echo "   Esperando inicio de la aplicación (20s)..."
sleep 20

# Obtener URL
APP_URL=$(az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" \
    -o tsv 2>/dev/null | tr -d '\r\n')

# =============================================================================
# RESULTADO
# =============================================================================
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ DESPLIEGUE COMPLETADO${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "🌐 ${BLUE}URL:${NC} https://$APP_URL"
echo -e "📦 ${BLUE}Imagen:${NC} $IMAGE_FULL"
echo -e "🕐 ${BLUE}Versión:${NC} $IMAGE_TAG"
echo ""
echo -e "🧪 ${YELLOW}Probar API:${NC}"
echo "   curl https://$APP_URL/api/person/15323375"
echo ""
echo -e "${GREEN}==========================================${NC}"
