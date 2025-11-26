from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import pandas as pd

class TxtFileReader:
    """
    Lee TXT (CSV-like) robusto:
    - encoding: intenta utf-8-sig y latin-1
    - separador: coma por defecto; puedes cambiarlo si tu fuente es otro
    - mantiene strings (sin NA)
    """
    def read(self, ruta_txt: Path) -> Dict[str, Any]:
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(
                    ruta_txt,
                    sep=",",
                    engine="python",
                    dtype=str,
                    keep_default_na=False,
                    encoding=enc
                )
                # Normaliza encabezados
                df.columns = [c.strip() for c in df.columns]
                return {"empty": df.empty, "df": df, "encoding": enc}
            except Exception:
                continue
        # Si todo falla:
        return {"empty": True, "df": pd.DataFrame(), "encoding": None}