#!/bin/bash
# =============================================================================
# DEPLOY PANEL DE PERSONAS — Azure (Bicep IaC)
# Construye imágenes en ACR y actualiza la infraestructura declarativamente
# Uso: bash deploy/deploy.sh [--infra] [--app] [--tag v20250101]
# =============================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

RESOURCE_GROUP="panel-de-personas"
IMAGE_TAG="${TAG:-v$(date +%Y%m%d%H%M%S)}"
DEPLOY_INFRA=false
DEPLOY_APP=true

# Parsear argumentos
while [[ $# -gt 0 ]]; do
  case $1 in
    --infra) DEPLOY_INFRA=true; shift ;;
    --app)   DEPLOY_APP=true; shift ;;
    --tag)   IMAGE_TAG="$2"; shift 2 ;;
    --full)  DEPLOY_INFRA=true; DEPLOY_APP=true; shift ;;
    *) echo "Uso: $0 [--infra] [--app] [--tag v...] [--full]"; exit 1 ;;
  esac
done

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}🚀 DEPLOY PANEL DE PERSONAS — AZURE${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "   Infraestructura: $([ $DEPLOY_INFRA = true ] && echo 'SI' || echo 'no')"
echo -e "   Aplicación:      $([ $DEPLOY_APP = true ] && echo 'SI' || echo 'no')"
echo -e "   Tag:             $IMAGE_TAG"
echo ""

# ─── 1. Verificar sesión Azure ───────────────────────────────────────────────
echo -e "${YELLOW}[1/4]${NC} Verificando sesión en Azure..."
if ! az account show > /dev/null 2>&1; then
    az login
fi
SUBSCRIPTION=$(az account show --query "name" -o tsv | tr -d '\r\n')
echo -e "   ${GREEN}✓${NC} Conectado: $SUBSCRIPTION"

# ─── 2. Obtener ACR ──────────────────────────────────────────────────────────
ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv | tr -d '\r\n')
if [ -z "$ACR_NAME" ]; then
    echo -e "${RED}Error: No se encontró ACR. Ejecuta primero con --infra${NC}"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} ACR: $ACR_NAME"

# ─── 3. Desplegar infraestructura (Bicep) ────────────────────────────────────
if [ "$DEPLOY_INFRA" = true ]; then
    echo ""
    echo -e "${YELLOW}[2/4]${NC} Desplegando infraestructura con Bicep..."

    # Obtener sufijo del storage account existente
    UNIQUE_SUFFIX=$(az storage account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv | tr -d '\r\n' | sed 's/stpanel//')

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/../infra/main.bicep" \
        --parameters "$(dirname "$0")/../infra/parameters.prod.json" \
        --parameters uniqueSuffix="$UNIQUE_SUFFIX" \
                     backendImageTag="$IMAGE_TAG" \
                     frontendImageTag="$IMAGE_TAG" \
        --only-show-errors

    echo -e "   ${GREEN}✓${NC} Infraestructura actualizada"
else
    echo -e "${YELLOW}[2/4]${NC} Infraestructura: saltando (--infra no indicado)"
fi

# ─── 4. Build de imágenes en ACR ─────────────────────────────────────────────
if [ "$DEPLOY_APP" = true ]; then
    echo ""
    echo -e "${YELLOW}[3/4]${NC} Construyendo imágenes en ACR..."
    cd "$(dirname "$0")/.."

    # Backend
    echo "   Building backend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-backend:$IMAGE_TAG" \
        --image "panel-personas-backend:latest" \
        --file docker/Dockerfile.backend \
        . --only-show-errors

    # Frontend
    echo "   Building frontend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-frontend:$IMAGE_TAG" \
        --image "panel-personas-frontend:latest" \
        --file docker/Dockerfile.frontend \
        . --only-show-errors

    echo -e "   ${GREEN}✓${NC} Imágenes construidas: $IMAGE_TAG"

    # ─── 5. Actualizar Container Apps ────────────────────────────────────────
    echo ""
    echo -e "${YELLOW}[4/4]${NC} Actualizando Container Apps..."

    BACKEND_APP=$(az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(name,'backend')].name | [0]" -o tsv | tr -d '\r\n')

    FRONTEND_APP=$(az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(name,'frontend')].name | [0]" -o tsv | tr -d '\r\n')

    az containerapp update \
        --name "$BACKEND_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_NAME.azurecr.io/panel-personas-backend:$IMAGE_TAG" \
        --only-show-errors --output none

    az containerapp update \
        --name "$FRONTEND_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_NAME.azurecr.io/panel-personas-frontend:$IMAGE_TAG" \
        --only-show-errors --output none

    echo -e "   ${GREEN}✓${NC} Container Apps actualizadas"
fi

# ─── Resultado ───────────────────────────────────────────────────────────────
echo ""
FRONTEND_URL=$(az containerapp list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?contains(name,'frontend')].properties.configuration.ingress.fqdn | [0]" \
    -o tsv | tr -d '\r\n')

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ DEPLOY COMPLETADO${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e "🌐 URL: ${BLUE}https://$FRONTEND_URL${NC}"
echo -e "📦 Tag: $IMAGE_TAG"
echo ""
echo -e "🧪 Probar: curl https://$FRONTEND_URL/api/health"
echo -e "${GREEN}==========================================${NC}"