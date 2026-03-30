"""
Utilidad para validación y normalización de RUTs chilenos
"""
import re

class RutValidator:
    
    @staticmethod
    def normalize_rut(rut_input):
        """
        Normaliza un RUT a formato numérico sin dígito verificador
        Entrada: '18.063.844-K', '18063844-K', '18063844'
        Salida: '18063844'
        """
        if not rut_input:
            return None
            
        # Convertir a string y limpiar
        rut_str = str(rut_input).strip().upper()
        
        # Remover puntos y espacios
        rut_str = rut_str.replace('.', '').replace(' ', '')
        
        # Si tiene guión, tomar solo la parte antes del guión
        if '-' in rut_str:
            rut_str = rut_str.split('-')[0]
        
        # Verificar que solo contenga números
        if not rut_str.isdigit():
            return None
            
        return rut_str
    
    @staticmethod
    def extract_dv_from_input(rut_input):
        """
        Extrae el dígito verificador del input si existe
        """
        if not rut_input:
            return None
            
        rut_str = str(rut_input).strip().upper()
        
        if '-' in rut_str:
            parts = rut_str.split('-')
            if len(parts) == 2 and len(parts[1]) == 1:
                return parts[1]
        
        return None
    
    @staticmethod
    def calculate_dv(rut_number):
        """
        Calcula el dígito verificador de un RUT chileno
        Algoritmo oficial chileno
        """
        if not rut_number:
            return None
            
        try:
            rut_str = str(rut_number).strip()
            if not rut_str.isdigit():
                return None
                
            # Algoritmo chileno para calcular DV
            sequence = [2, 3, 4, 5, 6, 7]
            sum_total = 0
            
            # Recorrer el RUT de derecha a izquierda
            for i, digit in enumerate(reversed(rut_str)):
                multiplier = sequence[i % len(sequence)]
                sum_total += int(digit) * multiplier
            
            remainder = sum_total % 11
            dv = 11 - remainder
            
            if dv == 11:
                return '0'
            elif dv == 10:
                return 'K'
            else:
                return str(dv)
                
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def validate_rut_format(rut_input):
        """
        Valida que el formato del RUT sea correcto
        """
        if not rut_input:
            return False, "RUT vacío"
            
        rut_str = str(rut_input).strip().upper()
        
        # Patrón mejorado para RUT chileno:
        # Opciones válidas:
        # 1. XX.XXX.XXX-X (formato con puntos)
        # 2. XXXXXXXX-X (formato sin puntos)  
        # 3. XXXXXXX o XXXXXXXX (solo números, sin DV)
        pattern = r'^\d{1,2}\.\d{3}\.\d{3}-[0-9K]$|^\d{7,8}-[0-9K]$|^\d{7,8}$'
        
        if not re.match(pattern, rut_str):
            return False, "Formato de RUT inválido"
        
        # Si tiene guión, verificar que después hay solo un carácter
        if '-' in rut_str:
            parts = rut_str.split('-')
            if len(parts) != 2 or len(parts[1]) != 1:
                return False, "Dígito verificador debe ser un solo carácter"
        
        return True, "Formato válido"
    
    @staticmethod
    def validate_rut_dv(rut_input):
        """
        Valida que el dígito verificador sea correcto
        """
        format_valid, format_msg = RutValidator.validate_rut_format(rut_input)
        if not format_valid:
            return False, format_msg
        
        # Extraer número y DV del input
        rut_number = RutValidator.normalize_rut(rut_input)
        dv_input = RutValidator.extract_dv_from_input(rut_input)
        
        if not rut_number:
            return False, "No se pudo extraer el número del RUT"
        
        # Si no hay DV en el input, no validamos DV (solo formato)
        if not dv_input:
            return True, "RUT sin DV - formato válido"
        
        # Calcular DV correcto
        dv_calculated = RutValidator.calculate_dv(rut_number)
        
        if dv_calculated != dv_input:
            return False, f"Dígito verificador incorrecto. Debería ser {dv_calculated}"
        
        return True, "RUT válido"
    
    @staticmethod
    def is_persona_natural(rut_number):
        """
        Verifica si un RUT corresponde a persona natural
        Regla: RUTs bajo 50.000.000 generalmente son personas naturales
        """
        try:
            rut_int = int(rut_number)
            return rut_int < 50000000
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_and_normalize(rut_input):
        """
        Función principal que valida y normaliza un RUT
        Retorna: (es_valido, rut_normalizado, mensaje)
        """
        if not rut_input:
            return False, None, "RUT vacío"
        
        # Validar formato
        format_valid, format_msg = RutValidator.validate_rut_format(rut_input)
        if not format_valid:
            return False, None, format_msg
        
        # Validar DV si está presente
        dv_valid, dv_msg = RutValidator.validate_rut_dv(rut_input)
        if not dv_valid:
            return False, None, dv_msg
        
        # Normalizar
        rut_normalized = RutValidator.normalize_rut(rut_input)
        if not rut_normalized:
            return False, None, "No se pudo normalizar el RUT"
        
        # Verificar que es persona natural
        if not RutValidator.is_persona_natural(rut_normalized):
            return False, None, "El RUT ingresado parece corresponder a una empresa"
        
        return True, rut_normalized, "RUT válido y normalizado"

# Ejemplos de uso:
if __name__ == "__main__":
    test_ruts = [
        "18.063.844-K",
        "18063844-K", 
        "18063844",
        "18.063.844-5",  # DV incorrecto
        "60.123.456-7",  # Empresa
        "abc-K",         # Formato inválido
    ]
    
    validator = RutValidator()
    
    for rut in test_ruts:
        valid, normalized, message = validator.validate_and_normalize(rut)
        print(f"RUT: {rut:15} | Válido: {valid:5} | Normalizado: {normalized:10} | {message}")
