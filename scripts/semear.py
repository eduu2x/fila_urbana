import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.semeador import semear_banco


if __name__ == "__main__":
    limpar = "--limpar" in sys.argv
    resultado = semear_banco(limpar=limpar)
    print(resultado["mensagem"])
    print(f"Demandas: {resultado['total_demandas']}")
    if "total_relatos" in resultado:
        print(f"Relatos: {resultado['total_relatos']}")
