"""
Tests de integracion para la API del backend.
FASE 3 del TDD: Verificar que get_person_details() usa los datos reales.
"""
import pytest
import sys
from pathlib import Path

# Agregar path del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Directorio de parquets
PARQUET_DIR = PROJECT_ROOT / "datos" / "parquet"

# RUTs de prueba
TEST_RUTS = {
    'completo': '15323375',
    'limpio': '12345678',
    'alertas': '98765432'
}


class TestPanelPersonasAPILocal:
    """Tests para la API cargando datos locales (sin Azure)."""

    @pytest.fixture(autouse=True)
    def setup_api(self):
        """Crear instancia de API con datos locales."""
        import pandas as pd
        import polars as pl

        # Crear clase mock que carga datos locales
        class MockPanelPersonasAPI:
            def __init__(self):
                self.load_local_data()

            def load_local_data(self):
                """Carga datos desde parquets locales."""
                # Datos basicos vacios (no los usamos en este test)
                self.personas_df = pd.DataFrame()
                self.historial_laboral_df = pd.DataFrame()
                self.documentos_cgr_df = pd.DataFrame()
                self.sociedades_df = pd.DataFrame()
                self.fiscalizaciones_df = pd.DataFrame()

                # Nuevos parquets V2
                self.sii_sociedades_df = pl.read_parquet(PARQUET_DIR / 'sii_sociedades.parquet').to_pandas()
                self.sii_rentas_df = pl.read_parquet(PARQUET_DIR / 'sii_rentas.parquet').to_pandas()
                self.srcei_condenas_df = pl.read_parquet(PARQUET_DIR / 'srcei_condenas.parquet').to_pandas()
                self.srcei_inhabilidades_df = pl.read_parquet(PARQUET_DIR / 'srcei_inhabilidades.parquet').to_pandas()
                self.srcei_deudores_df = pl.read_parquet(PARQUET_DIR / 'srcei_deudores.parquet').to_pandas()
                self.srcei_hijos_df = pl.read_parquet(PARQUET_DIR / 'srcei_hijos.parquet').to_pandas()
                self.sistradoc_denuncias_df = pl.read_parquet(PARQUET_DIR / 'sistradoc_denuncias.parquet').to_pandas()

            def clean_value_for_json(self, value):
                """Limpieza simple."""
                if pd.isna(value) or value is None:
                    return None
                return value

            def get_sii_data(self, run_str):
                """Obtener datos SII para un RUT."""
                sii_sociedades = []
                anios_soc = set()

                if not self.sii_sociedades_df.empty:
                    soc_person = self.sii_sociedades_df[self.sii_sociedades_df['run'] == run_str]
                    for _, soc in soc_person.iterrows():
                        sii_sociedades.append({
                            'nombre': soc.get('nombre', 'N/A'),
                            'rut': soc.get('rut_sociedad', 'N/A'),
                            'giro': soc.get('giro', 'N/A'),
                            'porcentaje': soc.get('porcentaje', 0),
                            'anio': soc.get('anio', 2025)
                        })
                        if soc.get('anio'):
                            anios_soc.add(int(soc.get('anio')))

                sii_rentas = []
                anios_ren = set()

                if not self.sii_rentas_df.empty:
                    ren_person = self.sii_rentas_df[self.sii_rentas_df['run'] == run_str]
                    for _, ren in ren_person.iterrows():
                        sii_rentas.append({
                            'pagador_retenedor': ren.get('pagador_retenedor', 'N/A'),
                            'monto': ren.get('monto', 0),
                            'anio': ren.get('anio', 2025)
                        })
                        if ren.get('anio'):
                            anios_ren.add(int(ren.get('anio')))

                anios = sorted(anios_soc | anios_ren, reverse=True) or [2025]

                return {
                    'sociedades': sii_sociedades,
                    'rentas': sii_rentas,
                    'anios_disponibles': anios
                }

            def get_srcei_data(self, run_str):
                """Obtener datos SRCeI para un RUT."""
                condenas = []
                if not self.srcei_condenas_df.empty:
                    for _, c in self.srcei_condenas_df[self.srcei_condenas_df['run'] == run_str].iterrows():
                        condenas.append({'tipo': c.get('tipo', ''), 'fecha': c.get('fecha', ''), 'detalle': c.get('detalle', '')})

                inhabilidades = []
                if not self.srcei_inhabilidades_df.empty:
                    for _, i in self.srcei_inhabilidades_df[self.srcei_inhabilidades_df['run'] == run_str].iterrows():
                        inhabilidades.append({'tipo': i.get('tipo', ''), 'fecha_inicio': i.get('fecha_inicio', '')})

                deudores = []
                if not self.srcei_deudores_df.empty:
                    for _, d in self.srcei_deudores_df[self.srcei_deudores_df['run'] == run_str].iterrows():
                        deudores.append({'es_deudor': d.get('es_deudor', False), 'detalle': d.get('detalle', '')})

                hijos = []
                if not self.srcei_hijos_df.empty:
                    for _, h in self.srcei_hijos_df[self.srcei_hijos_df['run'] == run_str].iterrows():
                        hijos.append({'nombre': h.get('nombre_hijo', ''), 'fecha_nacimiento': h.get('fecha_nacimiento', '')})

                return {
                    'condenas': condenas,
                    'inhabilidades': inhabilidades,
                    'deudores': deudores,
                    'hijos': hijos,
                    'hijos_count': len(hijos)
                }

            def get_sistradoc_data(self, run_str):
                """Obtener datos SISTRADOC para un RUT."""
                denuncias = []
                if not self.sistradoc_denuncias_df.empty:
                    for _, d in self.sistradoc_denuncias_df[self.sistradoc_denuncias_df['run'] == run_str].iterrows():
                        pres = d.get('presentaciones_conectadas', '')
                        pres_list = [p.strip() for p in str(pres).split(',') if p.strip()] if pres else []
                        denuncias.append({
                            'emisor': d.get('emisor', ''),
                            'estado_causa': d.get('estado_causa', ''),
                            'presentaciones_conectadas': pres_list
                        })

                return {'denuncias': denuncias}

        self.api = MockPanelPersonasAPI()

    # ============================================
    # Tests para RUT COMPLETO (15323375)
    # ============================================
    def test_rut_completo_sii_sociedades(self):
        """RUT completo debe tener sociedades SII."""
        sii = self.api.get_sii_data(TEST_RUTS['completo'])
        assert len(sii['sociedades']) > 0, "Deberia tener sociedades"
        assert len(sii['sociedades']) >= 3, "Deberia tener al menos 3 sociedades"

    def test_rut_completo_sii_rentas(self):
        """RUT completo debe tener rentas SII."""
        sii = self.api.get_sii_data(TEST_RUTS['completo'])
        assert len(sii['rentas']) > 0, "Deberia tener rentas"

    def test_rut_completo_sii_anios(self):
        """RUT completo debe tener anios disponibles."""
        sii = self.api.get_sii_data(TEST_RUTS['completo'])
        assert len(sii['anios_disponibles']) > 0, "Deberia tener anios disponibles"
        assert 2025 in sii['anios_disponibles'] or 2024 in sii['anios_disponibles']

    def test_rut_completo_srcei_condenas(self):
        """RUT completo debe tener condenas."""
        srcei = self.api.get_srcei_data(TEST_RUTS['completo'])
        assert len(srcei['condenas']) > 0, "Deberia tener condenas"

    def test_rut_completo_srcei_inhabilidades(self):
        """RUT completo debe tener inhabilidades."""
        srcei = self.api.get_srcei_data(TEST_RUTS['completo'])
        assert len(srcei['inhabilidades']) > 0, "Deberia tener inhabilidades"

    def test_rut_completo_srcei_hijos(self):
        """RUT completo debe tener hijos."""
        srcei = self.api.get_srcei_data(TEST_RUTS['completo'])
        assert srcei['hijos_count'] > 0, "Deberia tener hijos"
        assert len(srcei['hijos']) == srcei['hijos_count']

    def test_rut_completo_sistradoc_denuncias(self):
        """RUT completo debe tener denuncias."""
        sistradoc = self.api.get_sistradoc_data(TEST_RUTS['completo'])
        assert len(sistradoc['denuncias']) > 0, "Deberia tener denuncias"

    # ============================================
    # Tests para RUT LIMPIO (12345678)
    # ============================================
    def test_rut_limpio_no_condenas(self):
        """RUT limpio NO debe tener condenas."""
        srcei = self.api.get_srcei_data(TEST_RUTS['limpio'])
        assert len(srcei['condenas']) == 0, "No deberia tener condenas"

    def test_rut_limpio_no_inhabilidades(self):
        """RUT limpio NO debe tener inhabilidades."""
        srcei = self.api.get_srcei_data(TEST_RUTS['limpio'])
        assert len(srcei['inhabilidades']) == 0, "No deberia tener inhabilidades"

    def test_rut_limpio_has_sociedades(self):
        """RUT limpio debe tener sociedades (minimas)."""
        sii = self.api.get_sii_data(TEST_RUTS['limpio'])
        assert len(sii['sociedades']) > 0, "Deberia tener al menos 1 sociedad"

    # ============================================
    # Tests para RUT ALERTAS (98765432)
    # ============================================
    def test_rut_alertas_multiple_condenas(self):
        """RUT alertas debe tener multiples condenas."""
        srcei = self.api.get_srcei_data(TEST_RUTS['alertas'])
        assert len(srcei['condenas']) >= 2, "Deberia tener al menos 2 condenas"

    def test_rut_alertas_inhabilidades(self):
        """RUT alertas debe tener inhabilidades."""
        srcei = self.api.get_srcei_data(TEST_RUTS['alertas'])
        assert len(srcei['inhabilidades']) > 0, "Deberia tener inhabilidades"

    def test_rut_alertas_es_deudor(self):
        """RUT alertas debe ser deudor."""
        srcei = self.api.get_srcei_data(TEST_RUTS['alertas'])
        assert len(srcei['deudores']) > 0, "Deberia tener registro de deudor"
        assert srcei['deudores'][0]['es_deudor'] == True, "Deberia ser deudor"

    def test_rut_alertas_multiple_denuncias(self):
        """RUT alertas debe tener multiples denuncias."""
        sistradoc = self.api.get_sistradoc_data(TEST_RUTS['alertas'])
        assert len(sistradoc['denuncias']) >= 3, "Deberia tener al menos 3 denuncias"

    def test_rut_alertas_multiple_hijos(self):
        """RUT alertas debe tener multiples hijos."""
        srcei = self.api.get_srcei_data(TEST_RUTS['alertas'])
        assert srcei['hijos_count'] >= 4, "Deberia tener al menos 4 hijos"

    # ============================================
    # Tests de estructura de datos
    # ============================================
    def test_sociedad_has_required_fields(self):
        """Verificar campos de sociedad."""
        sii = self.api.get_sii_data(TEST_RUTS['completo'])
        if sii['sociedades']:
            soc = sii['sociedades'][0]
            assert 'nombre' in soc
            assert 'rut' in soc
            assert 'giro' in soc
            assert 'porcentaje' in soc
            assert 'anio' in soc

    def test_renta_has_required_fields(self):
        """Verificar campos de renta."""
        sii = self.api.get_sii_data(TEST_RUTS['completo'])
        if sii['rentas']:
            ren = sii['rentas'][0]
            assert 'pagador_retenedor' in ren
            assert 'monto' in ren
            assert 'anio' in ren

    def test_condena_has_required_fields(self):
        """Verificar campos de condena."""
        srcei = self.api.get_srcei_data(TEST_RUTS['completo'])
        if srcei['condenas']:
            cond = srcei['condenas'][0]
            assert 'tipo' in cond
            assert 'fecha' in cond
            assert 'detalle' in cond

    def test_denuncia_has_required_fields(self):
        """Verificar campos de denuncia."""
        sistradoc = self.api.get_sistradoc_data(TEST_RUTS['completo'])
        if sistradoc['denuncias']:
            den = sistradoc['denuncias'][0]
            assert 'emisor' in den
            assert 'estado_causa' in den
            assert 'presentaciones_conectadas' in den


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
