#!/bin/bash
# =============================================================================
# DEPLOY PANEL DE PERSONAS — Azure (Bicep IaC)
# Construye imágenes en ACR y actualiza la infraestructura declarativamente
#
# Uso:
#   bash deploy/deploy.sh --init          # Primera vez: crea TODO desde cero
#   bash deploy/deploy.sh --app           # Actualiza solo la app (día a día)
#   bash deploy/deploy.sh --infra         # Actualiza solo la infraestructura
#   bash deploy/deploy.sh --full          # Infra + app
#   bash deploy/deploy.sh --app --tag v1.2
# =============================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

RESOURCE_GROUP="panel-de-personas"
IMAGE_TAG="${TAG:-v$(date +%Y%m%d%H%M%S)}"
DEPLOY_INFRA=false
DEPLOY_APP=false
DEPLOY_INIT=false

# Parsear argumentos
while [[ $# -gt 0 ]]; do
  case $1 in
    --init)  DEPLOY_INIT=true; shift ;;
    --infra) DEPLOY_INFRA=true; shift ;;
    --app)   DEPLOY_APP=true; shift ;;
    --tag)   IMAGE_TAG="$2"; shift 2 ;;
    --full)  DEPLOY_INFRA=true; DEPLOY_APP=true; shift ;;
    *) echo "Uso: $0 [--init] [--app] [--infra] [--full] [--tag v...]"; exit 1 ;;
  esac
done

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   DEPLOY PANEL DE PERSONAS — AZURE${NC}"
echo -e "${BLUE}==========================================${NC}"

# ─── Verificar sesión Azure ──────────────────────────────────────────────────
echo -e "${YELLOW}[0/N]${NC} Verificando sesión en Azure..."
if ! az account show > /dev/null 2>&1; then
    az login
fi
SUBSCRIPTION=$(az account show --query "name" -o tsv | tr -d '\r\n')
echo -e "   ${GREEN}OK${NC} Conectado: $SUBSCRIPTION"

# =============================================================================
# MODO --init: Primera instalación completa desde cero
# =============================================================================
if [ "$DEPLOY_INIT" = true ]; then
    echo ""
    echo -e "${BLUE}  Modo INIT — primera instalación completa${NC}"
    echo -e "  Tag: $IMAGE_TAG"
    echo ""

    # ─── 1. Generar sufijo único ─────────────────────────────────────────────
    echo -e "${YELLOW}[1/5]${NC} Generando sufijo único para recursos Azure..."
    SUFIJO_FILE="$(dirname "$0")/.sufijo"

    if [ -f "$SUFIJO_FILE" ]; then
        UNIQUE_SUFFIX=$(cat "$SUFIJO_FILE")
        echo -e "   ${GREEN}OK${NC} Sufijo existente reutilizado: $UNIQUE_SUFFIX"
    else
        UNIQUE_SUFFIX=$(cat /dev/urandom | tr -dc a-z0-9 | head -c 6)
        echo "$UNIQUE_SUFFIX" > "$SUFIJO_FILE"
        echo -e "   ${GREEN}OK${NC} Nuevo sufijo generado: $UNIQUE_SUFFIX"
    fi
    echo -e "   Guardado en: $SUFIJO_FILE"

    # ─── 2. Primera pasada Bicep: crea ACR, Storage, KeyVault, etc. ─────────
    # Los Container Apps fallarán (imagen no existe aún) — es esperado
    echo ""
    echo -e "${YELLOW}[2/5]${NC} Desplegando infraestructura base con Bicep..."
    echo -e "   (Los Container Apps fallarán en esta pasada — es normal)"
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/../infra/main.bicep" \
        --parameters "$(dirname "$0")/../infra/parameters.prod.json" \
        --parameters uniqueSuffix="$UNIQUE_SUFFIX" \
                     backendImageTag="$IMAGE_TAG" \
                     frontendImageTag="$IMAGE_TAG" \
        --only-show-errors || true   # OK si falla en Container Apps

    # Verificar que ACR se creó (lo necesitamos para el build)
    ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null | tr -d '\r\n')
    if [ -z "$ACR_NAME" ]; then
        echo -e "${RED}Error: ACR no se creó. Revisa los errores anteriores.${NC}"
        exit 1
    fi
    echo -e "   ${GREEN}OK${NC} ACR listo: $ACR_NAME"

    # ─── 3. Build de imágenes Docker en ACR ──────────────────────────────────
    echo ""
    echo -e "${YELLOW}[3/5]${NC} Construyendo imágenes Docker en ACR..."
    cd "$(dirname "$0")/.."

    # En Windows, az acr build falla al traversar .venv (symlinks Unix de uv)
    # Se elimina antes del build — se recrea con `uv sync` después
    rm -rf .venv .venv_acr_tmp

    echo "   Building backend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-backend:$IMAGE_TAG" \
        --image "panel-personas-backend:latest" \
        --file docker/Dockerfile.backend \
        . --only-show-errors

    echo "   Building frontend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-frontend:$IMAGE_TAG" \
        --image "panel-personas-frontend:latest" \
        --file docker/Dockerfile.frontend \
        . --only-show-errors

    # Restaurar .venv
    echo -e "   ${GREEN}OK${NC} Imágenes construidas: $IMAGE_TAG"

    # ─── 4. Segunda pasada Bicep: ahora los Container Apps tienen imagen ──────
    echo ""
    echo -e "${YELLOW}[4/5]${NC} Desplegando Container Apps con imágenes reales..."
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/../infra/main.bicep" \
        --parameters "$(dirname "$0")/../infra/parameters.prod.json" \
        --parameters uniqueSuffix="$UNIQUE_SUFFIX" \
                     backendImageTag="$IMAGE_TAG" \
                     frontendImageTag="$IMAGE_TAG" \
        --only-show-errors

    echo -e "   ${GREEN}OK${NC} Infraestructura completa desplegada"

    # ─── 5. Subir parquets ────────────────────────────────────────────────────
    echo ""
    echo -e "${YELLOW}[5/5]${NC} Subiendo parquets a Blob Storage..."
    bash "$(dirname "$0")/upload_new_parquets.sh"

    # ─── Resultado final ──────────────────────────────────────────────────────
    FRONTEND_URL=$(az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(name,'frontend')].properties.configuration.ingress.fqdn | [0]" \
        -o tsv | tr -d '\r\n')

    echo ""
    echo -e "${GREEN}==========================================${NC}"
    echo -e "${GREEN}  INIT COMPLETADO${NC}"
    echo -e "${GREEN}==========================================${NC}"
    echo -e "  URL:    ${BLUE}https://$FRONTEND_URL${NC}"
    echo -e "  Tag:    $IMAGE_TAG"
    echo -e "  Sufijo: $UNIQUE_SUFFIX (en deploy/.sufijo)"
    echo -e "${GREEN}==========================================${NC}"
    echo ""
    echo -e "  Proximos deploys: bash deploy/deploy.sh --app"
    echo -e "${GREEN}==========================================${NC}"
    exit 0
fi

# =============================================================================
# MODOS --infra / --app / --full
# =============================================================================
echo -e "   Infraestructura: $([ $DEPLOY_INFRA = true ] && echo 'SI' || echo 'no')"
echo -e "   Aplicación:      $([ $DEPLOY_APP = true ] && echo 'SI' || echo 'no')"
echo -e "   Tag:             $IMAGE_TAG"
echo ""

# ─── Obtener ACR ─────────────────────────────────────────────────────────────
ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv | tr -d '\r\n')
if [ -z "$ACR_NAME" ]; then
    echo -e "${RED}Error: No se encontró ACR. Ejecuta primero: bash deploy/deploy.sh --init${NC}"
    exit 1
fi
echo -e "   ${GREEN}OK${NC} ACR: $ACR_NAME"

# ─── Desplegar infraestructura (Bicep) ───────────────────────────────────────
if [ "$DEPLOY_INFRA" = true ]; then
    echo ""
    echo -e "${YELLOW}[2/4]${NC} Desplegando infraestructura con Bicep..."

    SUFIJO_FILE="$(dirname "$0")/.sufijo"
    if [ -f "$SUFIJO_FILE" ]; then
        UNIQUE_SUFFIX=$(cat "$SUFIJO_FILE")
    else
        UNIQUE_SUFFIX=$(az storage account list \
            --resource-group "$RESOURCE_GROUP" \
            --query "[0].name" -o tsv | tr -d '\r\n' | sed 's/stpanel//')
    fi

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$(dirname "$0")/../infra/main.bicep" \
        --parameters "$(dirname "$0")/../infra/parameters.prod.json" \
        --parameters uniqueSuffix="$UNIQUE_SUFFIX" \
                     backendImageTag="$IMAGE_TAG" \
                     frontendImageTag="$IMAGE_TAG" \
        --only-show-errors

    echo -e "   ${GREEN}OK${NC} Infraestructura actualizada"
else
    echo -e "${YELLOW}[2/4]${NC} Infraestructura: saltando (usa --infra para actualizar)"
fi

# ─── Build de imágenes en ACR ─────────────────────────────────────────────────
if [ "$DEPLOY_APP" = true ]; then
    echo ""
    echo -e "${YELLOW}[3/4]${NC} Construyendo imágenes en ACR..."
    cd "$(dirname "$0")/.."

    # En Windows, az acr build falla al traversar .venv (symlinks inválidos)
    if [ -d ".venv" ]; then
        mv .venv .venv_acr_tmp
        trap 'mv .venv_acr_tmp .venv 2>/dev/null; exit' INT TERM EXIT
    fi

    echo "   Building backend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-backend:$IMAGE_TAG" \
        --image "panel-personas-backend:latest" \
        --file docker/Dockerfile.backend \
        . --only-show-errors

    echo "   Building frontend..."
    az acr build \
        --registry "$ACR_NAME" \
        --image "panel-personas-frontend:$IMAGE_TAG" \
        --image "panel-personas-frontend:latest" \
        --file docker/Dockerfile.frontend \
        . --only-show-errors

    echo -e "   ${GREEN}OK${NC} Imágenes construidas: $IMAGE_TAG"

    # ─── Actualizar Container Apps ────────────────────────────────────────────
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

    echo -e "   ${GREEN}OK${NC} Container Apps actualizadas"
fi

# ─── Resultado ────────────────────────────────────────────────────────────────
echo ""
FRONTEND_URL=$(az containerapp list \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?contains(name,'frontend')].properties.configuration.ingress.fqdn | [0]" \
    -o tsv | tr -d '\r\n')

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  DEPLOY COMPLETADO${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e "  URL: ${BLUE}https://$FRONTEND_URL${NC}"
echo -e "  Tag: $IMAGE_TAG"
echo ""
echo -e "  Probar: curl https://$FRONTEND_URL/api/health"
echo -e "${GREEN}==========================================${NC}"
