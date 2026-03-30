from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import polars as pl
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import sys
import json

# Agregar el directorio padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.utils.rut_validator import RutValidator

# Cargar .env desde la carpeta padre
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Apunta a la carpeta 'frontend' que está en el directorio raíz del proyecto
app = Flask(__name__, static_folder='../frontend')
CORS(app, origins=['http://127.0.0.1:8082', 'http://localhost:8082',
                    'http://127.0.0.1:8081', 'http://localhost:8081', 'file://', '*'],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'])


class PanelPersonasAPI:
    """API principal del Panel de Personas v2.
    
    Carga 10 archivos parquet y expone endpoints por pestaña.
    Usa LazyFrame para redes_familiares.parquet (57M filas) con filtro push-down.
    """

    def __init__(self):
        self.parquet_dir = Path(__file__).parent.parent / 'datos' / 'parquet'
        print(f"[INFO] Directorio parquets: {self.parquet_dir}")

        # DataFrames cargados en memoria (Polars nativo, NO pandas)
        self.inicio_df = None
        self.datos_generales_df = None
        self.rentas_df = None
        self.honorarios_df = None
        self.beneficiarios_df = None
        self.representantes_df = None
        self.socios_df = None
        self.siaper_df = None
        self.sistradoc_df = None

        # LazyFrame para redes_familiares (57M filas - NO cargar en memoria)
        self.redes_familiares_path = self.parquet_dir / 'redes_familiares.parquet'

        self._load_all_parquets()

    def _load_all_parquets(self):
        """Carga todos los parquets en memoria excepto redes_familiares."""
        parquet_map = {
            'inicio': ('inicio.parquet', 'inicio_df'),
            'datos_generales': ('datos_generales.parquet', 'datos_generales_df'),
            'rentas': ('rentas.parquet', 'rentas_df'),
            'honorarios': ('honorarios.parquet', 'honorarios_df'),
            'beneficiarios': ('beneficiarios.parquet', 'beneficiarios_df'),
            'representantes': ('representantes.parquet', 'representantes_df'),
            'socios_colaboradores': ('socios_colaboradores.parquet', 'socios_df'),
            'siaper': ('siaper.parquet', 'siaper_df'),
            'sistradoc': ('sistradoc.parquet', 'sistradoc_df'),
        }

        for name, (filename, attr) in parquet_map.items():
            filepath = self.parquet_dir / filename
            try:
                if filepath.exists():
                    df = pl.read_parquet(filepath)
                    setattr(self, attr, df)
                    print(f"   [OK] {filename}: {df.shape[0]:,} filas, {df.shape[1]} cols")
                else:
                    print(f"   [SKIP] {filename} no existe")
                    setattr(self, attr, pl.DataFrame())
            except Exception as e:
                print(f"   [ERROR] {filename}: {e}")
                setattr(self, attr, pl.DataFrame())

        # Verificar redes_familiares existe (se usa con LazyFrame)
        if self.redes_familiares_path.exists():
            # Solo verificar que se puede hacer scan
            lf = pl.scan_parquet(self.redes_familiares_path)
            print(f"   [OK] redes_familiares.parquet: LazyFrame listo (scan_parquet)")
        else:
            print(f"   [SKIP] redes_familiares.parquet no existe")

        print("[OK] Todos los parquets cargados.")

    # =========================================================================
    # UTILIDADES
    # =========================================================================
    def _df_to_records(self, df, max_rows=1000):
        """Convierte un Polars DataFrame a lista de diccionarios para JSON."""
        if df is None or df.is_empty():
            return []
        # Limitar filas
        if df.shape[0] > max_rows:
            df = df.head(max_rows)
        # Serializar via JSON nativo de Polars (maneja dates, nulls, etc.)
        return json.loads(df.write_json())

    def _get_run_key(self, df, run_str):
        """Determina la columna de RUN y filtra por RUN."""
        if df is None or df.is_empty():
            return pl.DataFrame()

        # Detectar columna de RUN
        run_cols = {
            'persona_run_sin_dv': 'persona_run_sin_dv',
            'funcionario_rut_sin_dv': 'funcionario_rut_sin_dv',
            'socio_rut_sin_dv': 'socio_rut_sin_dv',
            'representante_rut_sin_dv': 'representante_rut_sin_dv',
            'servidor_publico_run_sin_dv': 'servidor_publico_run_sin_dv',
            'rut': 'rut',
            'rut_persona': 'rut_persona',
        }

        for col_name in run_cols:
            if col_name in df.columns:
                col_dtype = df.schema[col_name]
                if col_dtype == pl.Int64 or col_dtype == pl.Int32:
                    try:
                        return df.filter(pl.col(col_name) == int(run_str))
                    except ValueError:
                        return pl.DataFrame()
                else:
                    return df.filter(pl.col(col_name) == run_str)

        return pl.DataFrame()

    def _get_unique_dates(self, df, run_str, date_col='fecha_actualizacion'):
        """Obtiene fechas únicas disponibles para un RUN."""
        filtered = self._get_run_key(df, run_str)
        if filtered.is_empty() or date_col not in filtered.columns:
            return []
        dates = filtered.select(pl.col(date_col)).unique().sort(date_col, descending=True)
        # Convertir a string
        return [str(d) for d in dates[date_col].to_list() if d is not None]

    def _filter_by_date(self, df, date_str, date_col='fecha_actualizacion'):
        """Filtra DataFrame por fecha de actualización."""
        if not date_str or date_col not in df.columns:
            return df
        try:
            from datetime import date as date_type
            # Intentar parsear la fecha
            parts = date_str.split('-')
            target_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
            return df.filter(pl.col(date_col) == target_date)
        except Exception:
            return df

    def _filter_by_anio(self, df, anio, anio_col='anio_tributario'):
        """Filtra DataFrame por año tributario."""
        if not anio or anio_col not in df.columns:
            return df
        try:
            return df.filter(pl.col(anio_col) == int(anio))
        except (ValueError, TypeError):
            return df

    def _deduplicate_snapshots(self, df, subset_cols=None):
        """Elimina duplicados cuando no hay filtro de fecha, ignorando la columna de fecha del snapshot.
        Si se provee subset_cols, deduplica usando solo esas columnas reales."""
        if df.is_empty():
            return df
        
        if subset_cols:
            cols_no_date = [c for c in subset_cols if c in df.columns]
        else:
            cols_no_date = [c for c in df.columns if c not in ('fecha_actualizacion', 'mes_foto')]
            
        if 'fecha_actualizacion' in df.columns:
            # Mantener la versión de la fecha más reciente si hay diferencias menores
            df = df.sort('fecha_actualizacion', descending=True)
            return df.unique(subset=cols_no_date, keep='first')
        return df.unique(subset=cols_no_date, keep='first')

    # =========================================================================
    # ENDPOINT: BÚSQUEDA (search)
    # =========================================================================
    def search_person(self, run_input):
        """Busca persona por RUN en inicio.parquet."""
        run_str = str(run_input).strip()
        result = self._get_run_key(self.inicio_df, run_str)

        if not result.is_empty():
            record = json.loads(result.head(1).write_json())[0]
            # Agregar RUT formateado
            dv = record.get('persona_dv', '')
            run = record.get('persona_run_sin_dv', run_str)
            record['rut'] = f"{run}-{dv}" if dv else str(run)
            return record, "Persona encontrada"
        return None, "Persona no encontrada"

    # =========================================================================
    # ENDPOINT: INICIO (indicadores del dashboard)
    # =========================================================================
    def get_inicio(self, run_str):
        """Obtiene indicadores de inicio para una persona."""
        result = self._get_run_key(self.inicio_df, run_str)
        if result.is_empty():
            return None
        record = json.loads(result.head(1).write_json())[0]
        dv = record.get('persona_dv', '')
        run = record.get('persona_run_sin_dv', run_str)
        record['rut'] = f"{run}-{dv}" if dv else str(run)
        return record

    # =========================================================================
    # ENDPOINT: DATOS PERSONALES
    # =========================================================================
    def get_datos_personales(self, run_str, fecha_actualizacion=None):
        """Obtiene datos generales + redes familiares filtrados."""
        # Datos generales (in-memory)
        dg = self._get_run_key(self.datos_generales_df, run_str)
        if fecha_actualizacion:
            dg = self._filter_by_date(dg, fecha_actualizacion)
        else:
            dg = self._deduplicate_snapshots(dg)

        # Redes familiares (LazyFrame con push-down)
        rf_records = []
        if self.redes_familiares_path.exists():
            try:
                lf = pl.scan_parquet(self.redes_familiares_path)
                # Push-down filter: solo lee las filas relevantes del disco
                run_int = int(run_str)
                filtered_lf = lf.filter(
                    pl.col('servidor_publico_run_sin_dv') == run_int
                )
                if fecha_actualizacion:
                    from datetime import date as date_type
                    parts = fecha_actualizacion.split('-')
                    target = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                    filtered_lf = filtered_lf.filter(
                        pl.col('fecha_actualizacion') == target
                    )
                # Collect solo las filas filtradas
                rf_df = filtered_lf.collect()
                if not fecha_actualizacion:
                    rf_df = self._deduplicate_snapshots(rf_df)
                
                # Limitar a máximo 1000 registros después de deduplicar
                if rf_df.shape[0] > 1000:
                    rf_df = rf_df.head(1000)
                
                rf_records = json.loads(rf_df.write_json())
            except Exception as e:
                print(f"[ERROR] LazyFrame redes_familiares: {e}")

        return {
            'datos_generales': self._df_to_records(dg),
            'redes_familiares': rf_records
        }

    def get_datos_personales_fechas(self, run_str):
        """Obtiene fechas únicas de datos_generales y redes_familiares."""
        fechas_dg = self._get_unique_dates(self.datos_generales_df, run_str)

        # Para redes_familiares, usar LazyFrame
        fechas_rf = []
        if self.redes_familiares_path.exists():
            try:
                lf = pl.scan_parquet(self.redes_familiares_path)
                run_int = int(run_str)
                dates_df = (
                    lf.filter(pl.col('servidor_publico_run_sin_dv') == run_int)
                    .select('fecha_actualizacion')
                    .unique()
                    .sort('fecha_actualizacion', descending=True)
                    .collect()
                )
                fechas_rf = [str(d) for d in dates_df['fecha_actualizacion'].to_list() if d is not None]
            except Exception as e:
                print(f"[ERROR] LazyFrame redes_familiares fechas: {e}")

        # Unir y deduplicar
        all_dates = sorted(set(fechas_dg + fechas_rf), reverse=True)
        return all_dates

    # =========================================================================
    # ENDPOINT: SII - RENTAS Y HONORARIOS
    # =========================================================================
    def get_sii_rentas_honorarios(self, run_str, anio_tributario=None):
        """Obtiene rentas + honorarios filtrados por año."""
        rentas = self._get_run_key(self.rentas_df, run_str)
        honorarios = self._get_run_key(self.honorarios_df, run_str)

        if anio_tributario:
            rentas = self._filter_by_anio(rentas, anio_tributario)
            honorarios = self._filter_by_anio(honorarios, anio_tributario)
        else:
            rentas = self._deduplicate_snapshots(rentas, subset_cols=['anio_tributario'])
            honorarios = self._deduplicate_snapshots(honorarios, subset_cols=['anio_tributario'])

        return {
            'rentas': self._df_to_records(rentas),
            'honorarios': self._df_to_records(honorarios)
        }

    def get_sii_anios(self, run_str):
        """Obtiene años tributarios disponibles."""
        anios = set()
        for df in [self.rentas_df, self.honorarios_df]:
            filtered = self._get_run_key(df, run_str)
            if not filtered.is_empty() and 'anio_tributario' in filtered.columns:
                vals = filtered['anio_tributario'].unique().to_list()
                anios.update([int(v) for v in vals if v is not None])
        return sorted(anios, reverse=True)

    # =========================================================================
    # ENDPOINT: SII - EMPRESAS
    # =========================================================================
    def get_sii_empresas(self, run_str, fecha_actualizacion=None):
        """Obtiene beneficiarios + representantes + socios filtrados."""
        benef = self._get_run_key(self.beneficiarios_df, run_str)
        repres = self._get_run_key(self.representantes_df, run_str)
        socios = self._get_run_key(self.socios_df, run_str)

        if fecha_actualizacion:
            benef = self._filter_by_date(benef, fecha_actualizacion)
            repres = self._filter_by_date(repres, fecha_actualizacion)
            socios = self._filter_by_date(socios, fecha_actualizacion)
        else:
            benef = self._deduplicate_snapshots(benef, subset_cols=['sociedad_rut_sin_dv'])
            repres = self._deduplicate_snapshots(repres, subset_cols=['sociedad_rut_sin_dv'])
            socios = self._deduplicate_snapshots(socios, subset_cols=['sociedad_rut_sin_dv'])

        return {
            'beneficiarios': self._df_to_records(benef),
            'representantes': self._df_to_records(repres),
            'socios_colaboradores': self._df_to_records(socios)
        }

    def get_sii_empresas_fechas(self, run_str):
        """Obtiene fechas únicas de empresas."""
        fechas = set()
        for df in [self.beneficiarios_df, self.representantes_df, self.socios_df]:
            f = self._get_unique_dates(df, run_str)
            fechas.update(f)
        return sorted(fechas, reverse=True)

    # =========================================================================
    # ENDPOINT: SIAPER
    # =========================================================================
    def get_siaper(self, run_str, fecha_actualizacion=None):
        """Obtiene historial laboral SIAPER."""
        result = self._get_run_key(self.siaper_df, run_str)
        if fecha_actualizacion:
            result = self._filter_by_date(result, fecha_actualizacion)
        else:
            result = self._deduplicate_snapshots(result)
        return self._df_to_records(result)

    def get_siaper_fechas(self, run_str):
        """Obtiene fechas únicas de SIAPER."""
        return self._get_unique_dates(self.siaper_df, run_str)

    # =========================================================================
    # ENDPOINT: SISTRADOC
    # =========================================================================
    def get_sistradoc(self, run_str, fecha_actualizacion=None):
        """Obtiene presentaciones SISTRADOC."""
        result = self._get_run_key(self.sistradoc_df, run_str)
        if fecha_actualizacion:
            result = self._filter_by_date(result, fecha_actualizacion)
        else:
            result = self._deduplicate_snapshots(result)
        return self._df_to_records(result)

    def get_sistradoc_fechas(self, run_str):
        """Obtiene fechas únicas de SISTRADOC."""
        return self._get_unique_dates(self.sistradoc_df, run_str)


# Descargar parquets desde Azure (si está configurada la credencial)
from backend.utils.azure_storage import download_parquets_if_needed
download_parquets_if_needed()

# Inicializar la API
print("[INFO] Inicializando Panel de Personas API v2...")
api = PanelPersonasAPI()


# ========== RUTAS DE LA API ==========

@app.route('/api/search', methods=['GET'])
def search_person():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Parámetro de búsqueda requerido'}), 400

    person, message = api.search_person(query)
    if person:
        return jsonify({'results': [person], 'type': 'run', 'message': message})
    else:
        return jsonify({'results': [], 'message': message, 'error': True}), 404


@app.route('/api/validate-rut', methods=['GET'])
def validate_rut():
    rut_input = request.args.get('rut', '').strip()
    if not rut_input:
        return jsonify({'error': 'Parámetro rut requerido'}), 400

    is_valid, rut_normalized, message = RutValidator.validate_and_normalize(rut_input)
    return jsonify({
        'valid': is_valid,
        'normalized': rut_normalized,
        'message': message,
        'input': rut_input
    })


# --- INICIO ---
@app.route('/api/inicio/<run>', methods=['GET'])
def get_inicio(run):
    data = api.get_inicio(run)
    if data:
        return jsonify(data)
    return jsonify({'error': 'Persona no encontrada'}), 404


# --- DATOS PERSONALES ---
@app.route('/api/datos-personales/<run>', methods=['GET'])
def get_datos_personales(run):
    fecha = request.args.get('fecha_actualizacion')
    data = api.get_datos_personales(run, fecha)
    return jsonify(data)


@app.route('/api/datos-personales/fechas/<run>', methods=['GET'])
def get_datos_personales_fechas(run):
    fechas = api.get_datos_personales_fechas(run)
    return jsonify(fechas)


# --- SII: RENTAS Y HONORARIOS ---
@app.route('/api/sii/rentas-honorarios/<run>', methods=['GET'])
def get_sii_rentas_honorarios(run):
    anio = request.args.get('anio_tributario')
    data = api.get_sii_rentas_honorarios(run, anio)
    return jsonify(data)


@app.route('/api/sii/rentas-honorarios/anios/<run>', methods=['GET'])
def get_sii_anios(run):
    anios = api.get_sii_anios(run)
    return jsonify(anios)


# --- SII: EMPRESAS ---
@app.route('/api/sii/empresas/<run>', methods=['GET'])
def get_sii_empresas(run):
    fecha = request.args.get('fecha_actualizacion')
    data = api.get_sii_empresas(run, fecha)
    return jsonify(data)


@app.route('/api/sii/empresas/fechas/<run>', methods=['GET'])
def get_sii_empresas_fechas(run):
    fechas = api.get_sii_empresas_fechas(run)
    return jsonify(fechas)


# --- SIAPER ---
@app.route('/api/siaper/<run>', methods=['GET'])
def get_siaper(run):
    fecha = request.args.get('fecha_actualizacion')
    data = api.get_siaper(run, fecha)
    return jsonify(data)


@app.route('/api/siaper/fechas/<run>', methods=['GET'])
def get_siaper_fechas(run):
    fechas = api.get_siaper_fechas(run)
    return jsonify(fechas)


# --- SISTRADOC ---
@app.route('/api/sistradoc/<run>', methods=['GET'])
def get_sistradoc(run):
    fecha = request.args.get('fecha_actualizacion')
    data = api.get_sistradoc(run, fecha)
    return jsonify(data)


@app.route('/api/sistradoc/fechas/<run>', methods=['GET'])
def get_sistradoc_fechas(run):
    fechas = api.get_sistradoc_fechas(run)
    return jsonify(fechas)


# --- UTILIDADES ---
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'message': 'Panel de Personas API v2 funcionando'})


@app.route('/api/suggestions', methods=['GET'])
def get_suggestions():
    return jsonify([])


# ========== RUTAS PARA SERVIR FRONTEND ==========
@app.route('/')
def serve_frontend():
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    html_path = os.path.join(frontend_dir, 'index.html')
    if not os.path.exists(html_path):
        return "Frontend no encontrado", 404

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/frontend/<path:filename>')
def serve_static(filename):
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    return send_from_directory(frontend_dir, filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port)