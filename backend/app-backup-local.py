from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

class PanelPersonasAPI:
    def __init__(self):
        self.data_file = 'datos_personas.xlsx'
        self.load_data()
    
    def load_data(self):
        """Carga los datos desde el archivo Excel"""
        try:
            # Cargar todas las pestañas del Excel
            self.personas_df = pd.read_excel(self.data_file, sheet_name='personas')
            self.historial_laboral_df = pd.read_excel(self.data_file, sheet_name='historial_laboral')
            self.documentos_cgr_df = pd.read_excel(self.data_file, sheet_name='documentos_cgr')
            self.sociedades_df = pd.read_excel(self.data_file, sheet_name='sociedades')
            self.fiscalizaciones_df = pd.read_excel(self.data_file, sheet_name='fiscalizaciones')
            
            print("Datos cargados exitosamente")
        except Exception as e:
            print(f"Error cargando datos: {e}")
            self.create_sample_data()
    
    def create_sample_data(self):
        """Crea datos de muestra si no existe el archivo"""
        print("Creando datos de muestra...")
        
        # Datos de personas
        personas_data = {
            'rut': ['15789234-5', '12345678-9', '98765432-1'],
            'nombres': ['María Alejandra', 'Juan Carlos', 'Ana Patricia'],
            'apellido_paterno': ['Silva', 'González', 'Martínez'],
            'apellido_materno': ['Pérez', 'López', 'Rodríguez'],
            'fecha_nacimiento': ['1982-03-15', '1975-08-22', '1990-12-05'],
            'nacionalidad': ['Chilena', 'Chilena', 'Chilena'],
            'estado_civil': ['Casada', 'Soltero', 'Divorciada'],
            'profesion': ['Ingeniera Comercial', 'Contador Auditor', 'Abogada'],
            'rsh_tramo': ['60% - Tramo 4', '40% - Tramo 2', '80% - Tramo 5'],
            'es_funcionario_publico': [True, True, False],
            'familiares_sector_publico': [5, 2, 0],
            'tiene_sociedades': [True, False, True],
            'ventas_mercado_publico': [1200000, 0, 850000]
        }
        
        # Historial laboral
        historial_laboral_data = {
            'rut': ['15789234-5', '15789234-5', '15789234-5', '12345678-9', '12345678-9'],
            'institucion': ['Ministerio de Hacienda', 'CORFO', 'Municipalidad de Santiago', 'SEREMI Salud', 'Hospital Salvador'],
            'cargo': ['Analista Senior', 'Jefa de Proyectos', 'Asesora', 'Contador', 'Jefe Administrativo'],
            'tipo_contrato': ['Contrata', 'Honorarios', 'Honorarios', 'Planta', 'Contrata'],
            'fecha_inicio': ['2020-01-15', '2018-03-01', '2017-06-15', '2019-04-01', '2015-01-01'],
            'fecha_termino': [None, '2020-01-14', '2018-02-28', None, '2019-03-31'],
            'remuneracion': [2850000, 2200000, 1800000, 3200000, 2100000],
            'estado': ['Activo', 'Finalizado', 'Finalizado', 'Activo', 'Finalizado']
        }
        
        # Documentos CGR
        documentos_data = {
            'rut': ['15789234-5', '15789234-5', '15789234-5', '12345678-9'],
            'numero_documento': ['2024/001234', '2023/004567', '2022/007890', '2024/002345'],
            'tipo_documento': ['Reclamo', 'Consulta', 'Denuncia', 'Consulta'],
            'materia': ['Remuneraciones', 'Probidad Administrativa', 'Irregularidades Administrativas', 'Concursos Públicos'],
            'fecha_ingreso': ['2024-03-15', '2023-08-22', '2022-12-10', '2024-05-20'],
            'estado': ['Finalizado', 'Finalizado', 'En Revisión', 'En Trámite'],
            'resultado': ['Acogido Parcialmente', 'Respondido', 'Pendiente', 'Pendiente']
        }
        
        # Sociedades
        sociedades_data = {
            'rut_persona': ['15789234-5', '15789234-5', '98765432-1'],
            'rut_sociedad': ['76123456-7', '77987654-3', '76555444-2'],
            'razon_social': ['Consultora Silva y Asociados Ltda.', 'Inversiones MSP SpA', 'Servicios Legales AMP Ltda.'],
            'participacion': ['50%', '25%', '60%'],
            'ventas_mercado_publico': [850000, 350000, 850000],
            'estado': ['Activa', 'Activa', 'Activa']
        }
        
        # Fiscalizaciones
        fiscalizaciones_data = {
            'rut': ['15789234-5', '12345678-9'],
            'numero_informe': ['IF-2023-0145', 'IF-2024-0089'],
            'tipo': ['Auditoría', 'Investigación Especial'],
            'servicio': ['CORFO', 'SEREMI Salud'],
            'fecha': ['2023-06-15', '2024-02-10'],
            'observacion': ['Sin observaciones', 'Observación menor en documentación']
        }
        
        # Crear DataFrames
        self.personas_df = pd.DataFrame(personas_data)
        self.historial_laboral_df = pd.DataFrame(historial_laboral_data)
        self.documentos_cgr_df = pd.DataFrame(documentos_data)
        self.sociedades_df = pd.DataFrame(sociedades_data)
        self.fiscalizaciones_df = pd.DataFrame(fiscalizaciones_data)
        
        # Guardar en Excel
        with pd.ExcelWriter(self.data_file, engine='openpyxl') as writer:
            self.personas_df.to_excel(writer, sheet_name='personas', index=False)
            self.historial_laboral_df.to_excel(writer, sheet_name='historial_laboral', index=False)
            self.documentos_cgr_df.to_excel(writer, sheet_name='documentos_cgr', index=False)
            self.sociedades_df.to_excel(writer, sheet_name='sociedades', index=False)
            self.fiscalizaciones_df.to_excel(writer, sheet_name='fiscalizaciones', index=False)
    
    def normalize_rut(self, rut):
        """Normaliza el formato del RUT"""
        if pd.isna(rut):
            return None
        rut = str(rut).strip().upper()
        # Remover puntos y guiones
        rut = re.sub(r'[.-]', '', rut)
        # Agregar guión antes del dígito verificador
        if len(rut) >= 2:
            rut = rut[:-1] + '-' + rut[-1]
        # NO agregar puntos para que coincida con los datos almacenados
        return rut
    
    def search_person_by_rut(self, rut):
        """Busca una persona por RUT"""
        rut_normalized = self.normalize_rut(rut)
        person = self.personas_df[self.personas_df['rut'] == rut_normalized]
        return person.iloc[0].to_dict() if not person.empty else None
    
    def search_person_by_name(self, name):
        """Busca personas por nombre"""
        name = name.lower()
        mask = (
            self.personas_df['nombres'].str.lower().str.contains(name, na=False) |
            self.personas_df['apellido_paterno'].str.lower().str.contains(name, na=False) |
            self.personas_df['apellido_materno'].str.lower().str.contains(name, na=False)
        )
        return self.personas_df[mask].to_dict('records')
    
    def get_person_details(self, rut):
        """Obtiene todos los detalles de una persona"""
        person = self.search_person_by_rut(rut)
        if not person:
            return None
        
        # Calcular edad
        birth_date = pd.to_datetime(person['fecha_nacimiento'])
        age = (datetime.now() - birth_date).days // 365
        




        # Obtener historial laboral y reemplazar NaN con None
        historial = self.historial_laboral_df[self.historial_laboral_df['rut'] == rut].to_dict('records')
        # Convertir NaN a None para JSON
        for record in historial:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        # Obtener documentos CGR
        documentos = self.documentos_cgr_df[self.documentos_cgr_df['rut'] == rut].to_dict('records')
        
        # Obtener sociedades
        sociedades = self.sociedades_df[self.sociedades_df['rut_persona'] == rut].to_dict('records')
        
        # Obtener fiscalizaciones
        fiscalizaciones = self.fiscalizaciones_df[self.fiscalizaciones_df['rut'] == rut].to_dict('records')
        
        # Estadísticas
        stats = {
            'documentos_count': len(documentos),
            'sociedades_count': len(sociedades),
            'familiares_sector_publico': person['familiares_sector_publico'],
            'ventas_mercado_publico': person['ventas_mercado_publico']
        }
        
        return {
            'persona': {**person, 'edad': age},
            'historial_laboral': historial,
            'documentos_cgr': documentos,
            'sociedades': sociedades,
            'fiscalizaciones': fiscalizaciones,
            'estadisticas': stats
        }

# Inicializar la API
api = PanelPersonasAPI()

@app.route('/api/search', methods=['GET'])
def search_person():
    """Endpoint para buscar personas"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Parámetro de búsqueda requerido'}), 400
    
    # Verificar si es un RUT (contiene guión o números)
    if '-' in query or query.replace('.', '').replace('-', '').isdigit():
        # Búsqueda por RUT
        person = api.search_person_by_rut(query)
        if person:
            return jsonify({'results': [person], 'type': 'rut'})
        else:
            return jsonify({'results': [], 'message': 'Persona no encontrada'}), 404
    else:
        # Búsqueda por nombre
        persons = api.search_person_by_name(query)
        return jsonify({'results': persons, 'type': 'name'})

@app.route('/api/person/<rut>', methods=['GET'])
def get_person_details(rut):
    """Endpoint para obtener detalles completos de una persona"""
    details = api.get_person_details(rut)
    
    if details:
        return jsonify(details)
    else:
        return jsonify({'error': 'Persona no encontrada'}), 404

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    """Endpoint para obtener sugerencias de búsqueda"""
    query = request.args.get('q', '').strip().lower()
    
    if len(query) < 2:
        return jsonify([])
    
    # Buscar coincidencias en nombres
    suggestions = []
    for _, person in api.personas_df.iterrows():
        full_name = f"{person['nombres']} {person['apellido_paterno']} {person['apellido_materno']}"
        if query in full_name.lower() or query in person['rut'].lower():
            suggestions.append({
                'rut': person['rut'],
                'nombre': full_name,
                'type': 'person'
            })
    
    return jsonify(suggestions[:5])  # Máximo 5 sugerencias

@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de salud"""
    return jsonify({'status': 'OK', 'message': 'Panel de Personas API funcionando'})

if __name__ == '__main__':
    print("Iniciando Panel de Personas API...")
    print("Documentación disponible en: http://localhost:5000/api/health")
    app.run(debug=True, host='0.0.0.0', port=5000)