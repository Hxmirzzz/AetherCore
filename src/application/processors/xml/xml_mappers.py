"""
Funciones puras de mapeo de elementos XML -> dicts crudos (sin IO).
Replica nombres de columnas, formato de fechas y denoms del procesador original.
"""
from __future__ import annotations
from datetime import datetime
from http import client
from typing import Dict, Any, List, Tuple
import logging, re
import xml.etree.ElementTree as ET

from src.infrastructure.config.mapeos import TextosConstantes, DenominacionesConfig, ClienteMapeos

logger = logging.getLogger(__name__)

def resolver_codigos_xml(codigo_raw: str, xml_name: str) -> Tuple[str, str, bool]:
    """
    Extrae el código del cliente, el código del punto limpio y si es sucursal.
    
    Args:
        codigo_raw: Código del punto como viene del XML (ej: "52-SUC-0075", "52-0075")
        xml_name: Nombre del archivo XML para fallback
        
    Returns:
        (client_code, punto_limpio, es_sucursal)
    """
    es_sucursal = "-SUC-" in codigo_raw
    codigo_limpio = codigo_raw.replace("-SUC-", "-")
    partes = codigo_limpio.split('-', 1)
    
    if len(partes) == 2:
        cc_code = partes[0]
        punto_limpio = partes[1].strip()
        
        cc_to_client = {v: k for k, v in ClienteMapeos.CLIENTE_TO_CC.items()}
        client_code = cc_to_client.get(cc_code, cc_code)

        return client_code, punto_limpio, es_sucursal
    
    client_code = extract_cc_from_filename(xml_name)
    return client_code, codigo_raw.strip(), es_sucursal

def _format_ddmmyyyy(yyyy_mm_dd: str) -> str:
    """
    Convierte fecha YYYY-MM-DD a DD/MM/YYYY.
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

def map_elements(elements: List[ET.Element], tipo_servicio: str) -> List[Dict[str, Any]]:
    """
    Mapea elementos XML (order o remit) a diccionarios listos para DataFrame.
    
    Args:
        elements: Lista de elementos XML (order o remit)
        tipo_servicio: "PROVISIÓN" o "RECOLECCIÓN" (de TextosConstantes)
        
    Returns:
        Lista de diccionarios, cada uno representa una fila de datos
    """
    filas: List[Dict[str, Any]] = []
    
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

        total = 0
        denoms_dict = {k: 0 for k in DenominacionesConfig.DENOMINACIONES}
        for denom_element in item.findall('.//denom'):
            code = denom_element.attrib.get('code', '')
            try:
                amount = float(denom_element.attrib.get('amount', '0'))
            except ValueError:
                amount = 0
            if code in denoms_dict:
                denoms_dict[code] = amount
                total += amount

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
            'ENTIDAD': '',
            'CODIGO': codigo_raw,
            'NOMBRE PUNTO': '',
            'TIPO DE SERVICIO': tipo_orden,
            'TRANSPORTADORA': transportadora,
            'CIUDAD': '',
        }
        for denom_key in DenominacionesConfig.DENOMINACIONES:
            col_name = _denom_col(denom_key)
            fila[col_name] = f"${int(denoms_dict[denom_key]):,}".replace(",", ".")
        fila['GENERAL'] = f"${int(total):,}".replace(",", ".")
        filas.append(fila)

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
        m = re.match(r'^\d{2}', partes[1][4:])
        if m: return m.group(0)
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
        if (len(partes) >= 5 and partes[3].isdigit() and len(partes[3]) == 8 and
            partes[4].lower().endswith('.xml') and partes[4][:-4].isdigit() and len(partes[4][:-4]) == 6):
            return datetime.strptime(partes[3] + partes[4][:-4], '%Y%m%d%H%M%S').strftime('%y%m%d%H%M%S')
    except Exception:
        pass
    return datetime.now().strftime('%y%m%d%H%M%S')