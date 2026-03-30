import os
from pathlib import Path
from azure.storage.blob import BlobServiceClient

def download_parquets_if_needed():
    """Descarga los archivos .parquet desde Azure Blob Storage si existe la cadena de conexión."""
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    if not connection_string:
        print("[INFO] AZURE_STORAGE_CONNECTION_STRING no detectada. Usando parquets locales.")
        return

    # Ubicamos la carpeta exactamente donde el backend la espera (../../datos/parquet)
    parquet_dir = Path(__file__).parent.parent.parent / 'datos' / 'parquet'
    parquet_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[{'AZURE'}] Conectando a Azure Blob Storage...")
    try:
        blob_client = BlobServiceClient.from_connection_string(connection_string)
        # Confirmar el nombre del container. Según el snippet, es 'parquets'
        container_client = blob_client.get_container_client('parquets') 
        
        # Listamos los blobs dentro del contenedor
        blobs_list = list(container_client.list_blobs())
        
        if not blobs_list:
            print("[WARN] El contenedor 'parquets' en Azure está vacío.")
            return

        print(f"[{'AZURE'}] Descargando {len(blobs_list)} parquets hacia {parquet_dir}...")
        
        for blob in blobs_list:
            blob_path = parquet_dir / blob.name
            print(f"   -> Descargando {blob.name}...")
            
            download_stream = container_client.download_blob(blob.name)
            with open(blob_path, 'wb') as f:
                f.write(download_stream.readall())
                
        print(f"[{'AZURE'}] Descarga finalizada con éxito.")
        
    except Exception as e:
        print(f"[ERROR] Ocurrió un fallo al intentar descargar desde Azure: {e}")
        print("[INFO] La API intentará iniciar con los parquets que ya estén localmente.")
