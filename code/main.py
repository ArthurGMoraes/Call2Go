"""
main.py — Pipeline principal do análise Flywheel
=================================================
Uso:
  python main.py [caminho_para_csv]

Exemplo:
  python main.py ../data/influencers.csv

Requer variáveis de ambiente:
  YOUTUBE_API_KEY
  TWITCH_CLIENT_ID
  TWITCH_CLIENT_SECRET

Saídas em ../results/:
  - flywheel_resultados.csv   → tabela completa de métricas
  - ranking_scores.png
  - flywheel_scatter.png
  - series_temporais.png
"""

import sys
import os
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

# Garante que src/ está no path quando rodado de qualquer lugar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ARQUIVO_CSV, RESULTS_DIR
from collector import coletar_criador
from metrics import analisar_criador
from charts import gerar_todos_graficos


# Leitura do CSV dos influencers
def carregar_csv(caminho: str) -> list[dict]:
    df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()
    df = df.fillna("").map(str.strip)
    df = df[df["nome_influencer"].ne("")].reset_index(drop=True)
    return df.to_dict(orient="records")

# CSV resultados
COLUNAS_CSV = [
    "nome", "jogo", "infantil",
    "yt_subscribers", "yt_n_posts", "yt_delta_medio", "yt_delta_desvio", "yt_score_medio",
    "tw_followers",   "tw_n_posts", "tw_delta_medio", "tw_delta_desvio", "tw_score_medio",
    "ratio_delta", "perfil",
]


def exportar_csv(resultados: list[dict]) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    caminho = os.path.join(RESULTS_DIR, "resultados.csv")

    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS_CSV, extrasaction="ignore")
        writer.writeheader()
        for r in resultados:
            writer.writerow({k: (f"{r[k]:.6f}" if isinstance(r[k], float) else r[k])
                             for k in COLUNAS_CSV})

    print(f"[OK] Resultados exportados: {caminho}")

def main():
    caminho_csv = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_CSV

    print(f"-Lendo CSV: {caminho_csv}")
    criadores = carregar_csv(caminho_csv)
    print(f"-{len(criadores)} criadores encontrados\n")

    # Coleta paralela
    dados_brutos = []
    print("-Iniciando coleta")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futuros = {executor.submit(coletar_criador, c): c for c in criadores}
        for futuro in as_completed(futuros):
            try:
                dados_brutos.append(futuro.result())
            except Exception as e:
                nome = futuros[futuro].get("nome_influencer", "?")
                print(f"[ERRO] Falha ao coletar '{nome}': {e}")

    print(f"\n-Dados coletados: {len(dados_brutos)} criadores")

    # Análise de métricas
    print("-Calculando métricas")
    resultados = [analisar_criador(d) for d in dados_brutos]

    # Exportar
    exportar_csv(resultados)

    # Gráficos
    print("-Gerando gráficos")
    gerar_todos_graficos(resultados, caminho_csv)

    print("\n-Pipeline concluído. Resultados em:", RESULTS_DIR)


if __name__ == "__main__":
    main()
