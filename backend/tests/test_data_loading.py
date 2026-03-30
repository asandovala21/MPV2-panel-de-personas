"""
Tests unitarios para carga de datos desde parquets locales.
FASE 2 del TDD: Verificar que los parquets se cargan correctamente.
"""
import pytest
import pandas as pd
import polars as pl
from pathlib import Path
import sys

# Agregar path del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Directorio de parquets de prueba
PARQUET_DIR = PROJECT_ROOT / "datos" / "parquet"

# RUTs de prueba definidos en generar_datos_prueba.py
TEST_RUTS = {
    'completo': '15323375',   # Tiene datos en todas las fuentes
    'limpio': '12345678',     # Datos minimos/limpios
    'alertas': '98765432'     # Multiples alertas
}


class TestParquetLoading:
    """Tests para verificar que los parquets se cargan correctamente."""

    def test_parquet_directory_exists(self):
        """Verificar que el directorio de parquets existe."""
        assert PARQUET_DIR.exists(), f"Directorio {PARQUET_DIR} no existe"

    def test_sii_sociedades_parquet_exists(self):
        """Verificar que sii_sociedades.parquet existe."""
        filepath = PARQUET_DIR / "sii_sociedades.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"

    def test_sii_sociedades_load_polars(self):
        """Cargar sii_sociedades con Polars."""
        filepath = PARQUET_DIR / "sii_sociedades.parquet"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de sociedades esta vacio"
        assert len(df) >= 3, f"Se esperaban al menos 3 registros, hay {len(df)}"

    def test_sii_sociedades_columns(self):
        """Verificar columnas de sii_sociedades."""
        filepath = PARQUET_DIR / "sii_sociedades.parquet"
        df = pl.read_parquet(filepath)
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'nombre', 'rut_sociedad', 'giro', 'porcentaje', 'anio']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada en sii_sociedades"

    def test_sii_rentas_parquet_exists(self):
        """Verificar que sii_rentas.parquet existe."""
        filepath = PARQUET_DIR / "sii_rentas.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"

    def test_sii_rentas_load_polars(self):
        """Cargar sii_rentas con Polars."""
        filepath = PARQUET_DIR / "sii_rentas.parquet"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de rentas esta vacio"

    def test_sii_rentas_columns(self):
        """Verificar columnas de sii_rentas."""
        filepath = PARQUET_DIR / "sii_rentas.parquet"
        df = pl.read_parquet(filepath)
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'pagador_retenedor', 'monto', 'tipo_formulario', 'anio']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada en sii_rentas"


class TestSRCeIParquets:
    """Tests para parquets de Registro Civil (SRCeI)."""

    def test_srcei_condenas_exists_and_loads(self):
        """Verificar srcei_condenas.parquet."""
        filepath = PARQUET_DIR / "srcei_condenas.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de condenas esta vacio"
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'tipo', 'fecha', 'detalle', 'tribunal']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada"

    def test_srcei_inhabilidades_exists_and_loads(self):
        """Verificar srcei_inhabilidades.parquet."""
        filepath = PARQUET_DIR / "srcei_inhabilidades.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de inhabilidades esta vacio"
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'tipo', 'fecha_inicio', 'fecha_termino', 'detalle']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada"

    def test_srcei_deudores_exists_and_loads(self):
        """Verificar srcei_deudores.parquet."""
        filepath = PARQUET_DIR / "srcei_deudores.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de deudores esta vacio"
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'es_deudor', 'detalle', 'fecha_registro']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada"

    def test_srcei_hijos_exists_and_loads(self):
        """Verificar srcei_hijos.parquet."""
        filepath = PARQUET_DIR / "srcei_hijos.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de hijos esta vacio"
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'nombre_hijo', 'fecha_nacimiento']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada"


class TestSISTRADOCParquet:
    """Tests para parquet de SISTRADOC."""

    def test_sistradoc_denuncias_exists_and_loads(self):
        """Verificar sistradoc_denuncias.parquet."""
        filepath = PARQUET_DIR / "sistradoc_denuncias.parquet"
        assert filepath.exists(), f"Archivo {filepath} no existe"
        df = pl.read_parquet(filepath)
        assert not df.is_empty(), "DataFrame de denuncias esta vacio"
        # Columnas reales segun generar_datos_prueba.py
        expected_cols = ['run', 'emisor', 'run_recurrente', 'estado_causa', 'presentaciones_conectadas', 'fecha_ingreso']
        for col in expected_cols:
            assert col in df.columns, f"Columna '{col}' no encontrada"


class TestDataByRUT:
    """Tests para verificar datos por RUT especifico."""

    def test_rut_completo_has_sociedades(self):
        """RUT completo (15323375) debe tener sociedades."""
        filepath = PARQUET_DIR / "sii_sociedades.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['completo'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['completo']} no tiene sociedades"

    def test_rut_completo_has_rentas(self):
        """RUT completo (15323375) debe tener rentas."""
        filepath = PARQUET_DIR / "sii_rentas.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['completo'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['completo']} no tiene rentas"

    def test_rut_completo_has_condenas(self):
        """RUT completo (15323375) debe tener condenas."""
        filepath = PARQUET_DIR / "srcei_condenas.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['completo'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['completo']} no tiene condenas"

    def test_rut_completo_has_hijos(self):
        """RUT completo (15323375) debe tener hijos."""
        filepath = PARQUET_DIR / "srcei_hijos.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['completo'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['completo']} no tiene hijos"

    def test_rut_completo_has_denuncias(self):
        """RUT completo (15323375) debe tener denuncias."""
        filepath = PARQUET_DIR / "sistradoc_denuncias.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['completo'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['completo']} no tiene denuncias"

    def test_rut_limpio_no_condenas(self):
        """RUT limpio (12345678) NO debe tener condenas."""
        filepath = PARQUET_DIR / "srcei_condenas.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['limpio'])
        assert len(filtered) == 0, f"RUT {TEST_RUTS['limpio']} tiene condenas (no deberia)"

    def test_rut_limpio_no_inhabilidades(self):
        """RUT limpio (12345678) NO debe tener inhabilidades."""
        filepath = PARQUET_DIR / "srcei_inhabilidades.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['limpio'])
        assert len(filtered) == 0, f"RUT {TEST_RUTS['limpio']} tiene inhabilidades (no deberia)"

    def test_rut_alertas_has_multiple_condenas(self):
        """RUT alertas (98765432) debe tener multiples condenas."""
        filepath = PARQUET_DIR / "srcei_condenas.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['alertas'])
        assert len(filtered) >= 2, f"RUT {TEST_RUTS['alertas']} deberia tener al menos 2 condenas"

    def test_rut_alertas_has_inhabilidades(self):
        """RUT alertas (98765432) debe tener inhabilidades."""
        filepath = PARQUET_DIR / "srcei_inhabilidades.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['alertas'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['alertas']} no tiene inhabilidades"

    def test_rut_alertas_is_deudor(self):
        """RUT alertas (98765432) debe ser deudor."""
        filepath = PARQUET_DIR / "srcei_deudores.parquet"
        df = pl.read_parquet(filepath)
        filtered = df.filter(pl.col('run') == TEST_RUTS['alertas'])
        assert len(filtered) > 0, f"RUT {TEST_RUTS['alertas']} no tiene registro de deudor"
        # Verificar que es_deudor sea True
        es_deudor = filtered[0, 'es_deudor']
        assert es_deudor == True, f"RUT {TEST_RUTS['alertas']} deberia ser deudor"


class TestDataIntegrity:
    """Tests de integridad de datos."""

    def test_all_ruts_are_strings(self):
        """Verificar que run sea string en todos los parquets."""
        parquet_files = [
            'sii_sociedades.parquet',
            'sii_rentas.parquet',
            'srcei_condenas.parquet',
            'srcei_inhabilidades.parquet',
            'srcei_deudores.parquet',
            'srcei_hijos.parquet',
            'sistradoc_denuncias.parquet'
        ]
        for filename in parquet_files:
            filepath = PARQUET_DIR / filename
            df = pl.read_parquet(filepath)
            dtype = df.schema['run']
            assert dtype == pl.Utf8, f"run en {filename} deberia ser String, es {dtype}"

    def test_dates_are_valid_format(self):
        """Verificar formato de fechas en condenas."""
        filepath = PARQUET_DIR / "srcei_condenas.parquet"
        df = pl.read_parquet(filepath)
        # Verificar que las fechas no sean nulas
        nulls = df.filter(pl.col('fecha').is_null())
        assert len(nulls) == 0, "Hay fechas nulas en condenas"

    def test_porcentaje_in_valid_range(self):
        """Verificar que porcentajes esten entre 0 y 100."""
        filepath = PARQUET_DIR / "sii_sociedades.parquet"
        df = pl.read_parquet(filepath)
        invalid = df.filter((pl.col('porcentaje') < 0) | (pl.col('porcentaje') > 100))
        assert len(invalid) == 0, f"Hay {len(invalid)} registros con porcentaje invalido"

    def test_montos_rentas_positive(self):
        """Verificar que los montos de rentas sean positivos."""
        filepath = PARQUET_DIR / "sii_rentas.parquet"
        df = pl.read_parquet(filepath)
        invalid = df.filter(pl.col('monto') < 0)
        assert len(invalid) == 0, f"Hay {len(invalid)} registros con monto negativo"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
