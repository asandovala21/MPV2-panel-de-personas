#!/bin/bash
### ESTE SCRIP SOLO SE EJECUTA LA PRIMERA VEZ PARA CREAR RECURSOS
# --- Configuración ---
RESOURCE_GROUP="panel-de-personas"
LOCATION="eastus2"

# --- Nombres de Recursos ---
UNIQUE_ID=$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)
STORAGE_ACCOUNT_NAME="stpocpersonas${UNIQUE_ID}"
ACR_NAME="acrpocpersonas${UNIQUE_ID}"
CONTAINER_APP_ENV="panel-env"
CONTAINER_APP_NAME="panel-app"
CONTAINER_NAME_BLOB="datos"

# --- Sección de Limpieza Automática ---
echo "🧹 Iniciando limpieza de recursos previos..."
az containerapp delete --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --yes &> /dev/null
az containerapp env delete --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --yes &> /dev/null
echo "✅ Limpieza completada. Procediendo con la creación de recursos."

# --- Creación de Recursos ---
echo "📝 Usando ID único para recursos: ${UNIQUE_ID}"
echo "📍 Ubicación fijada: ${LOCATION}"
az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS
echo "📦 Creando contenedor de blobs..."
az storage container create --name $CONTAINER_NAME_BLOB --account-name $STORAGE_ACCOUNT_NAME --auth-mode login
echo "⬆️  Subiendo archivos de datos Parquet..."
az storage blob upload-batch --account-name $STORAGE_ACCOUNT_NAME --destination $CONTAINER_NAME_BLOB --source ../datos/parquet --pattern "*.parquet" --auth-mode key
echo "🐳 Creando Azure Container Registry: ${ACR_NAME}..."
az acr create --name $ACR_NAME --resource-group $RESOURCE_GROUP --location $LOCATION --sku Basic --admin-enabled true
echo "🌳 Creando entorno de Container Apps: ${CONTAINER_APP_ENV}... (Esto puede tardar unos minutos)"
az containerapp env create --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --location $LOCATION
echo "⏳ Esperando a que el entorno de Container Apps esté listo..."
while [[ "$(az containerapp env show -n ${CONTAINER_APP_ENV} -g ${RESOURCE_GROUP} --query properties.provisioningState -o tsv)" != *"Succeeded"* ]]; do
  echo "   - Aún no está listo, esperando 30 segundos más..."
  sleep 30
done
echo "✅ ¡Entorno listo!"
CONNECTION_STRING=$(az storage account show-connection-string --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --query "connectionString" --output tsv)

# --- Crear la Container App ---
echo "🚀 Creando la Container App: ${CONTAINER_APP_NAME}..."
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
  --ingress 'external' \
  --registry-server "${ACR_NAME}.azurecr.io" \
  # El puerto de destino debe ser 80
  --target-port 80 \
  --secrets "storage-connection-string=$CONNECTION_STRING" \
  --env-vars "AZURE_STORAGE_CONNECTION_STRING=secretref:storage-connection-string"

echo "✅ ¡Configuración inicial completada!"
echo "➡️  ACR Name: $ACR_NAME"
echo "➡️  Container App Name: $CONTAINER_APP_NAME"
echo "Ahora, ejecuta 'deploy.sh' para construir y desplegar tu aplicación."