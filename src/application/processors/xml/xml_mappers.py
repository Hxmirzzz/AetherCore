"""
Funciones puras de mapeo de elementos XML -> dicts crudos (sin IO).
Replica nombres de columnas, formato de fechas y denoms del procesador original.
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any, List
import logging, re
import xml.etree.ElementTree as ET

from src.infrastructure.config.mapeos import TextosConstantes, DenominacionesConfig, ClienteMapeos

logger = logging.getLogger(__name__)

def _buscar_punto_con_fallbacks(codigo_raw: str, puntos_info: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """
    Busca un punto en puntos_info con múltiples estrategias de fallback.
    
    Estrategias (en orden):
    1. Búsqueda directa con el código tal cual viene del XML
    2. Si tiene formato "XX-SUC-YYYY", extraer solo "YYYY" y buscar
    3. Si tiene formato "CC-YYYY" donde CC es un CC Code, convertir a código de cliente y buscar "CLIENTE-YYYY"
    
    Args:
        codigo_raw: Código del punto como viene del XML (ej: "52-SUC-0075", "52-0075")
        puntos_info: Diccionario con información de puntos de la BD
        
    Returns:
        Diccionario con info del punto, o diccionario vacío si no se encuentra
    """
    punto_info = puntos_info.get(codigo_raw, {})
    if punto_info:
        logger.debug("Punto '%s' encontrado directamente", codigo_raw)
        return punto_info
    
    if "-SUC-" in codigo_raw:
        codigo_sin_suc = codigo_raw.split("-SUC-")[-1]
        punto_info = puntos_info.get(codigo_sin_suc, {})
        if punto_info:
            logger.info(
                "Punto '%s' encontrado usando formato sin SUC: '%s'",
                codigo_raw, codigo_sin_suc
            )
            return punto_info
    
    codigo_normalizado = codigo_raw.replace("-SUC-", "-")
    partes = codigo_normalizado.split('-', 1)
    
    if len(partes) == 2:
        posible_cc = partes[0]
        numero_punto = partes[1]
        
        cc_to_cliente = {v: k for k, v in ClienteMapeos.CLIENTE_TO_CC.items()}
        
        if posible_cc in cc_to_cliente:
            codigo_cliente = cc_to_cliente[posible_cc]
            codigo_convertido = f"{codigo_cliente}-{numero_punto}"
            
            punto_info = puntos_info.get(codigo_convertido, {})
            if punto_info:
                logger.info(
                    "Punto '%s' encontrado usando conversión CC->Cliente: '%s' (CC %s -> Cliente %s)",
                    codigo_raw, codigo_convertido, posible_cc, codigo_cliente
                )
                return punto_info
    
    logger.debug(
        "Punto '%s' no encontrado con ninguna estrategia. "
        "Intentos: directo='%s', sin SUC (si aplica), convertido (si aplica)",
        codigo_raw, codigo_raw
    )
    return {}

def _format_ddmmyyyy(yyyy_mm_dd: str) -> str:
    """
    Convierte fecha YYYY-MM-DD a DD/MM/YYYY.
    Si el formato no es válido, retorna la cadena original.
    """
    if not yyyy_mm_dd:
        return ""
    try:
        d = datetime.strptime(yyyy_mm_dd[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception as e:
        logger.warning("Formato de fecha inválido '%s': %s", yyyy_mm_dd, e)
        return yyyy_mm_dd

def _denom_col(denom_key: str) -> str:
    """
    Construye el nombre de columna para una denominación.
    Ejemplos:
        '100000' -> '$100000'
        '50000AD' -> '$50000 AD'
        '50000NF' -> '$50000 NF'
    """
    suf = denom_key[-2:]
    if suf in ("AD", "NF"):
        return f'${denom_key[:-2]} {suf}'
    return f'${denom_key}'

def map_elements(elements: List[ET.Element], tipo_servicio: str, puntos_info: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Mapea elementos XML (order o remit) a diccionarios listos para DataFrame.
    
    Args:
        elements: Lista de elementos XML (order o remit)
        tipo_servicio: "PROVISIÓN" o "RECOLECCIÓN" (de TextosConstantes)
        puntos_info: Diccionario con info de puntos de la BD
        
    Returns:
        Lista de diccionarios, cada uno representa una fila de datos
    """
    filas: List[Dict[str, Any]] = []
    
    logger.info("Procesando %d elementos de tipo '%s'", len(elements), tipo_servicio)
    
    for item in elements:
        id_elemento = item.attrib.get('id', '')
        delivery_date_raw = item.attrib.get('deliveryDate', '')
        order_date_raw = item.attrib.get('orderDate', '')
        pickup_date_raw = item.attrib.get('pickupDate', '')

        delivery_date_only = delivery_date_raw[:10] if delivery_date_raw else ''
        order_date_only = order_date_raw[:10] if order_date_raw else ''
        pickup_date_only = pickup_date_raw[:10] if pickup_date_raw else ''

        fecha_entrega = _format_ddmmyyyy(delivery_date_only)
        transportadora = (item.attrib.get('primaryTransport', '') or '').upper()

        entity = item.find('entity')
        codigo_raw = entity.attrib.get('entityReferenceID', '') if entity is not None else ''
        routing_number = entity.attrib.get('routingNumber', '') if entity is not None else ''
        cost_center = entity.attrib.get('costCenter', '') if entity is not None else ''

        fecha_solicitud = (
            order_date_only if tipo_servicio == TextosConstantes.SERVICIO_PROVISION_XML
            else pickup_date_only
        )
        
        mismo_dia = (fecha_solicitud == delivery_date_only) and (delivery_date_only != '')
        if mismo_dia and 'T' in (item.attrib.get('deliveryDate', '') or ''):
            hora_entrega = item.attrib.get('deliveryDate', '').split('T')[1][:5]
            rango_inicio = hora_entrega
        else:
            rango_inicio = (
                routing_number if tipo_servicio == TextosConstantes.SERVICIO_PROVISION_XML
                else cost_center
            )

        punto_info = _buscar_punto_con_fallbacks(codigo_raw, puntos_info)

        if not punto_info:
            nombre_punto = TextosConstantes.PUNTO_NO_ENCONTRADO_XML
            entidad = TextosConstantes.CLIENTE_NO_ENCONTRADO
            ciudad = TextosConstantes.CIUDAD_NO_ENCONTRADA
            logger.warning(
                "Punto con código '%s' (ID: '%s') no encontrado en BD",
                codigo_raw, id_elemento
            )
        else:
            nombre_punto = punto_info.get('nombre_punto', '')
            entidad = punto_info.get('nombre_cliente', '')
            ciudad = punto_info.get('ciudad', '')

        total = 0
        denoms_dict = {k: 0 for k in DenominacionesConfig.DENOMINACIONES}
        for denom_element in item.findall('.//denom'):
            code = denom_element.attrib.get('code', '')
            try:
                amount = float(denom_element.attrib.get('amount', '0'))
            except ValueError:
                amount = 0
                logger.warning(
                    "Valor 'amount' inválido '%s' para denominación '%s' en ID '%s'",
                    denom_element.attrib.get('amount', ''), code, id_elemento
                )
            if code in denoms_dict:
                denoms_dict[code] = amount
                total += amount
            else:
                logger.warning(
                    "Denominación '%s' no reconocida para ID '%s'",
                    code, id_elemento
                )

        order_type_val = item.attrib.get('orderType', '0')
        tipo_orden = (
            TextosConstantes.TIPO_ORDEN_NORMAL_XML
            if order_type_val == '0'
            else TextosConstantes.TIPO_ORDEN_EMERGENCIA_XML
        )
        
        fila = {
            'ID': id_elemento,
            'deliveryDate': delivery_date_raw,
            'orderDate': order_date_raw,
            'pickupDate': pickup_date_raw,
            'FECHA DE ENTREGA': fecha_entrega,
            'RANGO': rango_inicio,
            'ENTIDAD': entidad,
            'CODIGO': codigo_raw,
            'NOMBRE PUNTO': nombre_punto,
            'TIPO DE SERVICIO': tipo_orden,
            'TRANSPORTADORA': transportadora,
            'CIUDAD': ciudad,
        }
        for denom_key in DenominacionesConfig.DENOMINACIONES:
            col_name = _denom_col(denom_key)
            valor = denoms_dict[denom_key]
            fila[col_name] = f"${int(valor):,}".replace(",", ".")
        fila['GENERAL'] = f"${int(total):,}".replace(",", ".")
        filas.append(fila)

    logger.info("Procesados %d registros de tipo '%s'", len(filas), tipo_servicio)
    return filas

def extract_cc_from_filename(xml_name: str) -> str:
    """
    Extrae el CC Code del nombre del archivo XML.
    Formato esperado: ICOREX_C4U-XX-Vatco_...xml
    donde XX son dos dígitos.
    
    Returns:
        CC Code de 2 dígitos, o "00" si no se puede extraer
    """
    partes = xml_name.split('_')
    if len(partes) > 1 and partes[1].startswith('C4U-'):
        seg = partes[1][4:]
        m = re.match(r'^\d{2}', seg)
        if m: return m.group(0)
    logger.warning("No se pudo extraer CC Code de '%s', usando '00'", xml_name)
    return '00'

def build_timestamp_for_response(xml_name: str) -> str:
    """
    Construye el timestamp para el nombre del archivo de respuesta.
    Formato esperado en xml_name: ..._YYYYMMDD_HHMMSS.xml
    Formato de salida: YYMMDDHHMMSS (12 caracteres)
    
    Returns:
        Timestamp formateado, o timestamp actual si no se puede extraer
    """
    try:
        partes = xml_name.split('_')
        if (len(partes) >= 5 and
            partes[3].isdigit() and len(partes[3]) == 8 and
            partes[4].lower().endswith('.xml') and partes
            [4][:-4].isdigit() and len(partes[4][:-4]) == 6):
            fecha_str = partes[3]
            hora_str = partes[4][:-4]
            dt = datetime.strptime(fecha_str + hora_str, '%Y%m%d%H%M%S')
            return dt.strftime('%y%m%d%H%M%S')
    except Exception as e:
        logger.warning(
            "Error extrayendo timestamp de '%s': %s. Usando timestamp actual",
            xml_name, e
        )
    
    # Fallback: timestamp actual
    return datetime.now().strftime('%y%m%d%H%M%S')