"""
Uso:
  py main.py
  py main.py {caminho para o csv}
"""

import syspy 
import os
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# Garante que src/ está no path quando rodado de qualquer lugar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ARQUIVO_CSV, RESULTS_DIR
from collector import coletar_criador

#Carregando csv com influencers
def carregar_csv(caminho: str) -> list[dict]:
    df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()
    df = df.fillna("").map(str.strip)
    df = df[df["nome_influencer"].ne("")].reset_index(drop=True)
    return df.to_dict(orient="records")

#main
def main():
    caminho_csv = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_CSV

    print(f"-Lendo CSV: {caminho_csv}")
    criadores = carregar_csv(caminho_csv)
    print(f"-{len(criadores)} criadores encontrados\n")

    # Coleta paralela 
    dados_brutos = []
    print("-Iniciando coleta via APIs") 
    #4 workers
    with ThreadPoolExecutor(max_workers=4) as executor:
        futuros = {executor.submit(coletar_criador, c): c for c in criadores}
        for futuro in as_completed(futuros):
            try:
                dados_brutos.append(futuro.result())
            except Exception as e:
                nome = futuros[futuro].get("nome_influencer", "?")
                print(f"[ERRO] Falha ao coletar '{nome}': {e}")

    print(f"\n-Dados coletados: {len(dados_brutos)} criadores")

if __name__ == "__main__":
    main()
