from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from datetime import datetime

from src.infrastructure.config.mapeos import(
    TextosConstantes,
    TipoRutaMapeos,
    PrioridadMapeos,
    TipoPedidoMapeos
)

from src.domain.entities.catalogs import(
    CategoriaCatalogo,
    ServicioCatalogo,
    DivisaCatalogo
)

def parse_tipo_records(
    lines: List[str],
    dict_ciudades: Dict[str, str],
    dict_tipos_servicio: Dict[str, str],
    dict_categorias: Dict[str, str],
    dict_tipo_valor: Dict[str, str],
    dict_sucursales: Dict[str, Dict[str, str]],
    dict_clientes: Dict[str, Dict[str, str]],
) -> Tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    """
    Recibe líneas TXT con registros tipo 1/2/3 y devuelve:
    (df_tipo1, df_tipo2_pivot, df_tipo3) listos para exportar como en el XML.
    
    Usa los catálogos del dominio para mapeos de servicios, categorías y divisas.
    """
    t1, t2, t3 = [], [], []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        kind = s.split(",", 1)[0].strip()
        if kind == "1":
            t1.append(s.split(","))
        elif kind == "2":
            t2.append(s.split(","))
        elif kind == "3":
            t3.append(s.split(","))
            
    df1 = _crear_df_tipo1(t1) if t1 else None

    total_valor_tipo2_numeric = _sumar_valor_tipo2(t2) if t2 else 0
    df2 = _crear_df_tipo2(
        t2, dict_ciudades, dict_tipos_servicio, dict_categorias,
        dict_tipo_valor, dict_sucursales, dict_clientes
    ) if t2 else None

    df3 = _crear_df_tipo3(t3, total_valor_tipo2_numeric) if t3 else None
    return (df1, df2, df3)
    
    
# ========== HELPERS ==========
def _crear_df_tipo1(tipo1_data: List[List[str]]) -> pd.DataFrame:
    """Crea DataFrame de Tipo 1 (información general del archivo)"""
    df = pd.DataFrame(
        tipo1_data,
        columns=['TIPO REGISTRO', 'INTERFASE', 'APLICACION', 'FECHA GENERACION', 'SOLICITANTE', 'NIT CLIENTE']
    )
    df['FECHA GENERACION'] = pd.to_datetime(
        df['FECHA GENERACION'].astype(str).str.strip(), format='%d%m%Y', errors='coerce'
    ).dt.strftime('%d/%m/%Y').fillna('')
    df.drop(columns=['TIPO REGISTRO', 'INTERFASE', 'APLICACION'], inplace=True)
    return df

def _sumar_valor_tipo2(tipo2_data: List[List[str]]) -> int:
    """Suma el valor total de todos los registros Tipo 2"""
    total = 0
    for rec in tipo2_data:
        try:
            if len(rec) > 10:
                denom = int(rec[9].strip()) if rec[9].strip().isdigit() else 0
                cant  = int(rec[10].strip()) if rec[10].strip().isdigit() else 0
                total += denom * cant
        except Exception:
            pass
    return total

def _crear_df_tipo2(
    tipo2_data: List[List[str]],
    dict_ciudades: Dict[str, str],
    dict_tipos_servicio: Dict[str, str],
    dict_categorias: Dict[str, str],
    dict_tipo_valor: Dict[str, str],
    dict_sucursales: Dict[str, Dict[str, str]],
    dict_clientes: Dict[str, Dict[str, str]],
) -> pd.DataFrame:
    """
    Crea DataFrame de Tipo 2 (detalle de movimientos).

    1. Usa los catálogos del dominio como prioridad
    2. Replica EXACTAMENTE el comportamiento del código original
    3. NO agrupa filas por divisa
    """
    
    df = pd.DataFrame(
        tipo2_data,
        columns=[
            'TIPO REGISTRO','SERVICIO','CIUDAD','ACCION','FECHA SERVICIO','CODIGO PUNTO','NOMBRE PUNTO','CATEGORIA',
            'GAVETA','DENOMINACION','CANTIDAD','VALOR','PRIORIDAD','TIPO RUTA','TIPO PEDIDO','TIPO VALOR','CODIGO'
        ]
    )

    df['FECHA SERVICIO'] = pd.to_datetime(
        df['FECHA SERVICIO'].astype(str).str.strip(), format='%d%m%Y', errors='coerce'
    ).dt.strftime('%d/%m/%Y').fillna('')

    for col in ['DENOMINACION', 'CANTIDAD']:
        df[col] = pd.to_numeric(df[col].astype(str).str.strip(), errors='coerce').fillna(0).astype(int)

    df['VALOR_CALCULADO'] = df['DENOMINACION'] * df['CANTIDAD']

    df['DENOMINACION'] = df['DENOMINACION'].apply(lambda x: f"{x:,}".replace(",", "."))
    df['CANTIDAD'] = df['CANTIDAD'].apply(lambda x: f"{x:,}".replace(",", "."))
    df['VALOR_CALCULADO'] = df['VALOR_CALCULADO'].apply(lambda x: f"${x:,}".replace(",", "."))

    df['CIUDAD'] = df['CIUDAD'].astype(str).str.strip().apply(
        lambda x: f"{x} - {dict_ciudades.get(x, TextosConstantes.CIUDAD_NO_ENCONTRADA)}"
    )
    
    def _as_int_safe(v):
        try:
            return int(str(v).strip())
        except Exception:
            return None
        
    def _map_servicio(codigo_str: str) -> str:
        codigo = codigo_str.strip()
        codigo_int = _as_int_safe(codigo)
        
        if codigo_int is not None:
            desc = ServicioCatalogo.obtener_descripcion(codigo_int)
            if desc:
                return f"{codigo} - {desc}"
            
        if dict_tipos_servicio and codigo in dict_tipos_servicio:
            return f"{codigo} - {dict_tipos_servicio[codigo]}"
        
        return f"{codigo} - {TextosConstantes.TIPO_NO_ENCONTRADO}"
    df['SERVICIO'] = df['SERVICIO'].astype(str).apply(_map_servicio)
    
    df['CATEGORIA_CODE'] = df['CATEGORIA'].astype(str).str.strip()
    
    def _map_categoria(codigo_str: str) -> str:
        codigo = codigo_str.strip()
        codigo_int = _as_int_safe(codigo)
        
        if codigo_int is not None:
            desc = CategoriaCatalogo.obtener_descripcion(codigo_int)
            if desc:
                return f"{codigo} - {desc}"
            
        if dict_categorias and codigo in dict_categorias:
            return f"{codigo} - {dict_categorias[codigo]}"
        
        return f"{codigo} - {TextosConstantes.TIPO_NO_ENCONTRADO}"
    df['CATEGORIA'] = df['CATEGORIA'].astype(str).apply(_map_categoria)
    
    def _build_gaveta(row) -> str:
        gaveta_num = str(row['GAVETA']).strip()
        codigo_int = _as_int_safe(row['CATEGORIA_CODE'])
        
        desc = None
        if codigo_int is not None:
            desc = CategoriaCatalogo.obtener_descripcion(codigo_int)
        if not desc and dict_categorias:
            desc = dict_categorias.get(row['CATEGORIA_CODE'])
        if not desc:
            desc = TextosConstantes.CATEGORIA_NO_ENCONTRADA
        
        return f"GAV {gaveta_num} - {desc}"

    df['GAVETA'] = df.apply(_build_gaveta, axis=1)

    df['TIPO RUTA']   = df['TIPO RUTA'].astype(str).str.upper().str.strip()
    df['PRIORIDAD']   = df['PRIORIDAD'].astype(str).str.upper().str.strip()
    df['TIPO PEDIDO'] = df['TIPO PEDIDO'].astype(str).str.upper().str.strip()

    df['TIPO RUTA'] = df['TIPO RUTA'].apply(
        lambda code: TipoRutaMapeos.get_descripcion(code)
    )
    
    def _map_prioridad(row):
        if row['TIPO RUTA'] == 'DIURNO':
            desc = PrioridadMapeos.get_descripcion(row['PRIORIDAD'])
            return desc if desc else row['PRIORIDAD']
        return ''
    df['PRIORIDAD'] = df.apply(_map_prioridad, axis=1)

    df['TIPO PEDIDO'] = df['TIPO PEDIDO'].apply(
        lambda code: TipoPedidoMapeos.get_descripcion(code)
    )
    
    def _map_tipo_valor(codigo_str: str) -> str:
        codigo = codigo_str.strip()
        
        codigo_resuelto, divisa = DivisaCatalogo.resolver_divisa(codigo)
        if codigo_resuelto and divisa:
            return f"{codigo_resuelto} - {divisa}"
        
        if dict_tipo_valor and codigo in dict_tipo_valor:
            return f"{codigo_resuelto} - {dict_tipo_valor[codigo]}"
        
        return f"{codigo} - {TextosConstantes.TIPO_NO_ENCONTRADO}"

    df['TIPO VALOR'] = df['TIPO VALOR'].astype(str).apply(_map_tipo_valor)
    tipo_valor_por_codigo = (
        df.groupby('CODIGO')['TIPO VALOR']
        .apply(lambda s: next((v for v in s if v), ''))
        .to_dict()
    )

    def _suc(cod: str) -> str:
        if pd.isna(cod) or not str(cod).strip():
            return TextosConstantes.SUCURSAL_NO_ENCONTRADA
        info = dict_sucursales.get(str(cod).strip(), {})
        return info.get("sucursal", TextosConstantes.SUCURSAL_NO_ENCONTRADA)

    def _suc_code(cod: str) -> str:
        if pd.isna(cod) or not str(cod).strip():
            return "N/A"
        info = dict_sucursales.get(str(cod).strip(), {})
        return info.get("cod_suc", "N/A")

    def _cli(cod: str) -> str:
        if pd.isna(cod) or not str(cod).strip():
            return TextosConstantes.CLIENTE_NO_ENCONTRADO
        info = dict_clientes.get(str(cod).strip(), {})
        return info.get("cliente", TextosConstantes.CLIENTE_NO_ENCONTRADO)

    df['SUCURSAL']       = df['CODIGO PUNTO'].apply(_suc)
    df['COD_SUC_INTERNO']= df['CODIGO PUNTO'].apply(_suc_code)
    df['CLIENTE']        = df['CODIGO PUNTO'].apply(_cli)

    df.drop(columns=['CATEGORIA', 'CATEGORIA_CODE', 'TIPO REGISTRO', 'ACCION', 'VALOR'], inplace=True, errors='ignore')

    id_vars = [
        'CODIGO', 'FECHA SERVICIO', 'PRIORIDAD', 'CLIENTE', 'SERVICIO', 'CODIGO PUNTO', 'NOMBRE PUNTO',
        'CIUDAD', 'SUCURSAL', 'COD_SUC_INTERNO', 'TIPO RUTA', 'TIPO PEDIDO',
    ]

    gav_df = df[id_vars + ['GAVETA', 'DENOMINACION', 'CANTIDAD', 'VALOR_CALCULADO']].copy()
    
    gav_df_melted = gav_df.melt(
        id_vars=id_vars + ['GAVETA', 'VALOR_CALCULADO'],
        value_vars=['DENOMINACION', 'CANTIDAD'],
        var_name='METRICA',
        value_name='VALOR_METRICA'
    )
    
    gav_df_melted['GAVETA_METRICA_NOMBRE'] = gav_df_melted['GAVETA'] + ' ' + gav_df_melted['METRICA']
    
    pivot_df = gav_df_melted.pivot_table(
        index=id_vars,
        columns='GAVETA_METRICA_NOMBRE',
        values='VALOR_METRICA',
        aggfunc='first'
    ).reset_index()
    pivot_df.columns.name = None
    pivot_df['TIPO VALOR'] = pivot_df['CODIGO'].astype(str).map(tipo_valor_por_codigo).fillna('')
    
    all_gav_cols = [col for col in pivot_df.columns if isinstance(col, str) and col.startswith('GAV')]
    
    def _extract_gav_number(col_name):
        try:
            return int(col_name.split('GAV ')[1].split(' ')[0])
        except:
            return 99999
    
    cols_denominacion = sorted(
        [col for col in all_gav_cols if 'DENOMINACION' in col],
        key=_extract_gav_number
    )
    cols_cantidad = sorted(
        [col for col in all_gav_cols if 'CANTIDAD' in col],
        key=_extract_gav_number
    )

    def parse_formatted_num(x):
        """Convierte valores formateados a int"""
        if pd.isna(x) or x == '':
            return 0
        s = str(x).replace('$', '').replace('.', '').replace(',', '')
        try:
            return int(s)
        except ValueError:
            return 0

    pivot_df['CANT. BILLETE'] = pivot_df[cols_cantidad].apply(
        lambda row: sum(parse_formatted_num(x) for x in row),
        axis=1
    )

    pivot_df['TOTAL_VALOR'] = 0.0
    for i, row in pivot_df.iterrows():
        row_total = 0.0
        for col_denom in cols_denominacion:
            col_cant = col_denom.replace('DENOMINACION', 'CANTIDAD')
            if col_cant in pivot_df.columns:
                denom = parse_formatted_num(row[col_denom])
                cant = parse_formatted_num(row[col_cant])
                row_total += denom * cant
        pivot_df.at[i, 'TOTAL_VALOR'] = row_total

    pivot_df['CANT. BILLETE'] = pivot_df['CANT. BILLETE'].apply(lambda x: f"{int(x):,}".replace(",", "."))
    pivot_df['TOTAL_VALOR'] = pivot_df['TOTAL_VALOR'].apply(lambda x: f"${int(x):,}".replace(",", "."))

    for col in cols_denominacion:
        pivot_df[col] = pivot_df[col].apply(
            lambda x: f"${parse_formatted_num(x):,}".replace(",", ".") if pd.notna(x) and parse_formatted_num(x) != 0 else "$0"
        )

    columnas_base = [col for col in pivot_df.columns if col in id_vars]
    if 'TIPO VALOR' in pivot_df.columns and 'TIPO VALOR' not in columnas_base:
        columnas_base.append('TIPO VALOR')
    columnas_totales = ['TOTAL_VALOR', 'CANT. BILLETE']
    
    columnas_finales = columnas_base + columnas_totales + cols_denominacion + cols_cantidad
    columnas_finales = [col for col in columnas_finales if col in pivot_df.columns]
    pivot_df = pivot_df[columnas_finales]

    return pivot_df

def _crear_df_tipo3(tipo3_data: List[List[str]], total_valor_tipo2: int = 0) -> pd.DataFrame:
    """Crea DataFrame de Tipo 3 (totales del archivo)"""
    df = pd.DataFrame(
        tipo3_data,
        columns=['TIPO REGISTRO','INTERFASE','APLICACION','FECHA GENERACION','SOLICITANTE','NIT CLIENTE','TOTAL REGISTROS','TOTAL BILLETE']
    )
    df['FECHA GENERACION'] = pd.to_datetime(
        df['FECHA GENERACION'].astype(str).str.strip(), format='%d%m%Y', errors='coerce'
    ).dt.strftime('%d/%m/%Y').fillna('')

    for c in ['TOTAL REGISTROS','TOTAL BILLETE']:
        df[c] = pd.to_numeric(df[c].astype(str).str.strip(), errors='coerce').fillna(0).astype(int)
        df[c] = df[c].apply(lambda v: f"{v:,}".replace(",", "."))

    df['TOTAL VALOR'] = f"${int(total_valor_tipo2):,}".replace(",", ".")
    df.drop(columns=['TIPO REGISTRO','INTERFASE','APLICACION'], inplace=True)
    return df