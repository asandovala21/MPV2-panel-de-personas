"""
Panel de Personas CGR - Punto de entrada principal
Ejecuta la API o realiza el despliegue en Azure
"""
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Panel de Personas CGR - Aplicación Web")
    parser.add_argument(
        'command', 
        choices=['api', 'deploy'],
        help='Comando a ejecutar: api (iniciar servidor) o deploy (desplegar en Azure)'
    )
    parser.add_argument('--port', type=int, default=8081, help='Puerto para la API')
    parser.add_argument('--host', default='0.0.0.0', help='Host para la API')
    parser.add_argument('--debug', action='store_true', help='Modo debug')
    
    args = parser.parse_args()
    
    if args.command == 'api':
        print("🚀 Iniciando API del Panel de Personas...")
        run_api(args.port, args.host, args.debug)
        
    elif args.command == 'deploy':
        print("🔷 Ejecutando despliegue en Azure...")
        run_azure_deploy()

def run_api(port=5000, host='0.0.0.0', debug=False):
    """Ejecuta la API Flask"""
    try:
        import os
        
        # Configurar variables de entorno
        os.environ['PORT'] = str(port)
        os.environ['HOST'] = host
        if debug:
            os.environ['FLASK_ENV'] = 'development'
            os.environ['FLASK_DEBUG'] = 'true'
        
        # Actualizar configuración del frontend
        update_frontend_config(port)
        
        print(f"🌐 Iniciando servidor en http://{host}:{port}")
        print(f"🎨 Frontend disponible en: http://{host}:{port}")
        if debug:
            print("🐛 Modo debug activado")
        
        # Ejecutar la API
        cmd = [sys.executable, 'backend/app.py']
        subprocess.run(cmd, cwd=Path.cwd())
        
    except KeyboardInterrupt:
        print("\n⏹️ Servidor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error ejecutando API: {e}")

def update_frontend_config(port):
    """Actualiza la configuración del puerto en el frontend"""
    try:
        frontend_html = Path('frontend/index.html')
        if not frontend_html.exists():
            print("⚠️ Archivo frontend/index.html no encontrado")
            return
            
        # Leer contenido actual
        content = frontend_html.read_text(encoding='utf-8')
        
        # Buscar y reemplazar la configuración del API
        import re
        
        # Patrón para encontrar la línea de configuración
        pattern = r"const API_BASE_URL = [^;]+;"
        replacement = f"const API_BASE_URL = '/api';"
        
        # Reemplazar
        new_content = re.sub(pattern, replacement, content)
        
        # Escribir de vuelta
        frontend_html.write_text(new_content, encoding='utf-8')
        
        print(f"✅ Frontend configurado para puerto {port}")
        
    except Exception as e:
        print(f"⚠️ No se pudo actualizar configuración del frontend: {e}")
        print("   El frontend puede requerir configuración manual")

def run_azure_deploy():
    """Ejecuta despliegue en Azure"""
    try:
        deploy_script = Path('deploy/deploy.sh')
        if deploy_script.exists():
            print("🔄 Ejecutando script de despliegue...")
            
            if sys.platform.startswith('win'):
                # En Windows, ejecutar con bash (WSL) o Git Bash
                cmd = ['bash', str(deploy_script)]
            else:
                cmd = ['sh', str(deploy_script)]
            
            result = subprocess.run(cmd, cwd=Path.cwd())
            
            if result.returncode == 0:
                print("✅ Despliegue completado exitosamente")
            else:
                print("❌ Error en el despliegue")
        else:
            print("❌ Script de despliegue no encontrado: deploy/deploy.sh")
            print("� Verifica que el archivo deploy/deploy.sh existe")
            
    except Exception as e:
        print(f"❌ Error ejecutando despliegue: {e}")

if __name__ == "__main__":
    main()