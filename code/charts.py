"""
charts.py — Visualizações do análise flywheel
==============================================
Gera gráficos salvos em results/:
  1. tabela_influencers.png   — tabela formatada com todos os criadores
  2. relatorio_plataformas.png — dashboard: plataforma × jogo e × infantil
  3. ranking_scores.png       — score YT vs Twitch por criador
  4. flywheel_scatter.png     — scatter: correlação × ratio_delta
  5. series_temporais.png     — série de scores ao longo do tempo
"""

import sys
import os
import math
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from config import (
    FUNDO, FUNDO2, TEXTO, DESTAQUE, BORDA,
    CORES_PLATAFORMA, RESULTS_DIR, PLATAFORMAS,ARQUIVO_CSV
)

#Helpers internos
def _salvar(fig, nome_arquivo: str) -> None:
    """Garante que a pasta existe e salva o arquivo."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    caminho = os.path.join(RESULTS_DIR, nome_arquivo)
    fig.savefig(caminho, dpi=150, bbox_inches="tight", facecolor=FUNDO)
    plt.close(fig)
    print(f"[OK] Gráfico salvo: {caminho}")


def _aplicar_estilo(ax, titulo: str) -> None:
    ax.set_facecolor(FUNDO2)
    ax.tick_params(colors=TEXTO, labelsize=20)
    ax.set_title(titulo, color=DESTAQUE, fontsize=20, fontweight="bold", pad=20,
                 fontfamily="monospace")
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDA)
    ax.yaxis.grid(True, color=BORDA, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)


def _aplicar_estilo_eixo(ax, titulo: str) -> None:
    ax.set_facecolor(FUNDO2)
    ax.tick_params(colors=TEXTO, labelsize=20)
    ax.set_title(titulo, color=DESTAQUE, fontsize=20, fontweight="bold", pad=20)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDA)
    ax.title.set_fontfamily("monospace")

# Leitura do CSV de influencers
def carregar_dados(caminho: str) -> pd.DataFrame:
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        sys.exit(1)

    df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    faltando = {"nome_influencer", "nome_jogo"} - set(df.columns)
    if faltando:
        print(f"[ERRO] Colunas obrigatórias ausentes: {faltando}")
        sys.exit(1)

    for col in PLATAFORMAS.values():
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("").map(str.strip)
    df["nome_influencer"] = df["nome_influencer"].str.strip()
    df["nome_jogo"]       = df["nome_jogo"].str.strip()
    df = df[df["nome_influencer"].ne("")].reset_index(drop=True)

    if "infantil" not in df.columns:
        df["infantil"] = "n"
    df["infantil"] = df["infantil"].str.lower().map(lambda v: v == "s")

    for nome, col in PLATAFORMAS.items():
        df[f"tem_{nome}"] = df[col].ne("").astype(int)

    return df

#Tabela de influencers
def gerar_tabela(df: pd.DataFrame) -> None:
    plt.rcParams.update({"font.family": "monospace", "figure.facecolor": FUNDO, "text.color": TEXTO})

    df = df.copy()
    freq = df["nome_jogo"].value_counts()
    df["freq_jogo"] = df["nome_jogo"].map(freq)
    df = df.sort_values(
        by=["freq_jogo", "infantil", "nome_jogo", "nome_influencer"],
        ascending=[False, False, True, True]
    ).drop(columns="freq_jogo")

    def icone(url): return "✔" if str(url).strip() else "·"
    def inf_label(v): return "Yes" if v else "No"

    linhas = [
        [row["nome_influencer"], row["nome_jogo"],
         icone(row.get("link_youtube", "")), icone(row.get("link_twitch", "")),
         icone(row.get("link_discord", "")), inf_label(row["infantil"])]
        for _, row in df.iterrows()
    ]

    colunas = ["Name", "Game", "YouTube", "Twitch", "Discord", "Kids"]
    fig, ax = plt.subplots(figsize=(13, max(3.5, 0.45 * len(linhas) + 1.5)), facecolor=FUNDO)
    ax.set_facecolor(FUNDO)
    ax.axis("off")

    tabela = ax.table(cellText=linhas, colLabels=colunas, loc="center", cellLoc="center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(10)
    tabela.scale(1, 1.6)

    col_widths = [0.26, 0.18, 0.10, 0.10, 0.10, 0.10]
    for (ri, ci), cell in tabela.get_celld().items():
        cell.set_width(col_widths[ci])
        cell.set_edgecolor(BORDA)
        cell.set_linewidth(0.5)
        if ri == 0:
            cell.set_facecolor(DESTAQUE)
            cell.set_text_props(color=FUNDO, fontweight="bold", fontsize=10)
        elif ri % 2 == 0:
            cell.set_facecolor(FUNDO)
            cell.set_text_props(color=TEXTO)
        else:
            cell.set_facecolor(FUNDO2)
            cell.set_text_props(color=TEXTO)
        if ci in (0, 1):
            cell.set_text_props(ha="left")
            cell.PAD = 0.04
        if ri > 0 and ci in (2, 3, 4):
            cell.set_text_props(color="#C8FF00" if linhas[ri-1][ci] == "✔" else "#555566")
        if ri > 0 and ci == 5:
            cell.set_text_props(color="#FFD166" if linhas[ri-1][5] == "Yes" else TEXTO)

    fig.suptitle("Creators", color=DESTAQUE, fontsize=20,
                 fontweight="bold", fontfamily="monospace", y=0.98)
    fig.text(0.5, 0.01,
             f"Total: {len(df)}  |  Kid: {df['infantil'].sum()}  |  Adult: {(~df['infantil']).sum()}",
             ha="center", color=TEXTO, fontsize=20, alpha=0.6)
    _salvar(fig, "tabela_influencers.png")


#Dashboard: plataforma × jogo e × infantil
def _grafico_por_jogo(ax, df: pd.DataFrame) -> None:
    jogos, plataformas = df["nome_jogo"].unique(), list(PLATAFORMAS.keys())
    x, n, lw = range(len(jogos)), len(PLATAFORMAS), 0.25

    for i, plat in enumerate(plataformas):
        valores = [df[df["nome_jogo"] == j][f"tem_{plat}"].sum() for j in jogos]
        offset  = (i - n / 2 + 0.5) * lw
        barras  = ax.bar([xi + offset for xi in x], valores, width=lw,
                         color=CORES_PLATAFORMA[plat], label=plat,
                         edgecolor=FUNDO, linewidth=1.2)
        for b, v in zip(barras, valores):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05,
                        str(v), ha="center", va="bottom", color=TEXTO, fontsize=8)

    max_val = max(df[df["nome_jogo"] == j][f"tem_{p}"].sum()
                  for j in jogos for p in plataformas)
    ax.set_xticks(list(x))
    ax.set_xticklabels(jogos, rotation=25, ha="right", color=TEXTO, fontsize=9)
    ax.set_ylabel("Nº de Influencers", color=TEXTO, fontsize=10)
    ax.set_ylim(0, max_val * 1.35)
    ax.set_yticks(range(0, max_val + 2))
    ax.yaxis.grid(True, color=BORDA, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(facecolor=FUNDO, edgecolor=BORDA, labelcolor=TEXTO, fontsize=9, loc="upper right")
    _aplicar_estilo_eixo(ax, "Influencers por Jogo e Plataforma")


def _grafico_plataforma_infantil(ax, df: pd.DataFrame) -> None:
    plataformas = list(PLATAFORMAS.keys())
    x, acumulado = range(len(plataformas)), [0] * len(plataformas)

    for label, flag, cor in [("Adult", False, "#4B9CD3"), ("Kids", True, "#FFD166")]:
        valores = [df[(df[f"tem_{p}"] == 1) & (df["infantil"] == flag)].shape[0] for p in plataformas]
        barras  = ax.bar(list(x), valores, width=0.5, bottom=acumulado,
                         color=cor, label=label, edgecolor=FUNDO, linewidth=1.0)
        for b, v, base in zip(barras, valores, acumulado):
            if v > 0:
                ax.text(b.get_x() + b.get_width() / 2, base + v / 2, str(v),
                        ha="center", va="center", color=TEXTO, fontsize=20, fontweight="bold")
        acumulado = [a + v for a, v in zip(acumulado, valores)]

    for xi, total in zip(x, acumulado):
        ax.text(xi, total + 0.15, str(total), ha="center", va="bottom",
                color=TEXTO, fontsize=20, fontweight="bold")

    max_total = max(acumulado) if acumulado else 1
    ax.set_ylim(0, max_total * 1.25)
    ax.set_yticks(range(0, max_total + 2))
    ax.set_xticks(list(x))
    ax.set_xticklabels(plataformas)
    for tick, plat in zip(ax.get_xticklabels(), plataformas):
        tick.set_color(CORES_PLATAFORMA[plat])
        tick.set_fontweight("bold")
        tick.set_fontsize(20)
    ax.set_ylabel("Number of creators", color=TEXTO, fontsize=20)
    ax.yaxis.grid(True, color=BORDA, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)
    ax.legend(facecolor=FUNDO, edgecolor=BORDA, labelcolor=TEXTO, fontsize=20, loc="upper right")
    _aplicar_estilo_eixo(ax, "Plataform × Kids-content")


def gerar_graficos(df: pd.DataFrame) -> None:
    plt.rcParams.update({"font.family": "monospace", "figure.facecolor": FUNDO,
                          "axes.facecolor": FUNDO2, "text.color": TEXTO})
    fig = plt.figure(figsize=(20, 12), facecolor=FUNDO)
    fig.suptitle("DASHBOARD DE INFLUENCERS", color=DESTAQUE, fontsize=20,
                 fontweight="bold", fontfamily="monospace", y=0.98)
    gs  = GridSpec(1, 2, figure=fig, wspace=0.35, left=0.07, right=0.97, top=0.91, bottom=0.08)
    _grafico_plataforma_infantil(fig.add_subplot(gs[0, 0]), df)
    _grafico_por_jogo(fig.add_subplot(gs[0, 1]), df)
    fig.text(0.5, 0.02, f"Total de influencers analisados: {len(df)}",
             ha="center", color=TEXTO, fontsize=20, alpha=0.6)
    _salvar(fig, "relatorio_plataformas.png")


#Ranking de scores YT × Twitch
def grafico_ranking_scores(resultados: list[dict]) -> None:

    #YOUTUBE
    dados_yt = sorted(
        [r for r in resultados if (r["yt_score_medio"] or 0) > 0],
        key=lambda r: r["yt_score_medio"], reverse=True
    )
    nomes_yt  = [r["nome"] for r in dados_yt]
    scores_yt = [r["yt_score_medio"] for r in dados_yt]
    x_yt      = range(len(nomes_yt))

    fig, ax = plt.subplots(figsize=(max(12, len(nomes_yt) * 0.6), 8), facecolor=FUNDO)
    fig.suptitle("RANKING DE SCORES — YOUTUBE", color=DESTAQUE,
                 fontsize=15, fontweight="bold", fontfamily="monospace")

    barras = ax.bar(list(x_yt), scores_yt, width=0.6,
                    color=CORES_PLATAFORMA["YouTube"],
                    edgecolor=FUNDO, linewidth=0.8)

    for barra, v in zip(barras, scores_yt):
        ax.text(barra.get_x() + barra.get_width() / 2,
                barra.get_height() + 0.002,
                f"{v:.3f}", ha="center", va="bottom",
                color=TEXTO, fontsize=11, alpha=0.8, rotation=25)

    ax.set_xticks(list(x_yt))
    ax.set_xticklabels(nomes_yt, rotation=35, ha="right", color=TEXTO, fontsize=8)
    ax.set_ylabel("Score médio", color=TEXTO)
    _aplicar_estilo(ax, "Score médio por criador — YouTube")
    _salvar(fig, "ranking_scores_yt.png")

    #Twitch
    dados_tw = sorted(
        [r for r in resultados if (r["tw_score_medio"] or 0) > 0],
        key=lambda r: r["tw_score_medio"], reverse=True
    )
    nomes_tw  = [r["nome"] for r in dados_tw]
    scores_tw = [r["tw_score_medio"] for r in dados_tw]
    x_tw      = range(len(nomes_tw))

    fig2, ax2 = plt.subplots(figsize=(max(12, len(nomes_tw) * 0.70), 8), facecolor=FUNDO)
    fig2.suptitle("RANKING DE SCORES — TWITCH", color=DESTAQUE,
                  fontsize=15, fontweight="bold", fontfamily="monospace")

    barras2 = ax2.bar(list(x_tw), scores_tw, width=0.6,
                      color=CORES_PLATAFORMA["Twitch"],
                      edgecolor=FUNDO, linewidth=0.8)

    for barra, v in zip(barras2, scores_tw):
        ax2.text(barra.get_x() + barra.get_width() / 2,
                 barra.get_height() + 0.002,
                 f"{v:.3f}", ha="center", va="bottom",
                 color=TEXTO, fontsize=11, alpha=0.8, rotation=25)

    ax2.set_xticks(list(x_tw))
    ax2.set_xticklabels(nomes_tw, rotation=35, ha="right", color=TEXTO, fontsize=8)
    ax2.set_ylabel("Score médio", color=TEXTO)
    _aplicar_estilo(ax2, "Score médio por criador — Twitch")
    _salvar(fig2, "ranking_scores_tw.png")

# Grafico ratio delta 
def grafico_ratio(resultados: list[dict]) -> None:
    data = [r for r in resultados if (r["ratio_delta"] or 0) > 0]

    nomes = [r["nome"] for r in data]
    ratio = [r["ratio_delta"] for r in data]

    ratio_log = [math.log2(r) for r in ratio]

    y = range(len(nomes))

    fig, ax = plt.subplots(
        figsize=(20, max(6, len(nomes) * 0.4)),
        facecolor=FUNDO
    )

    fig.suptitle(
        "RATIO DELTA",
        color=DESTAQUE,
        fontsize=15,
        fontweight="bold",
        fontfamily="monospace"
    )

    cor = [CORES_PLATAFORMA["Twitch"] if r > 1 else CORES_PLATAFORMA["YouTube"] for r in ratio]

    barras = ax.barh(
        y,
        ratio_log,
        color = cor,
        edgecolor=FUNDO,
        linewidth=0.8
    )

    # linha de equilíbrio
    ax.axvline(
        0,
        color=TEXTO,
        linestyle="--",
        linewidth=1.5,
        alpha=0.8
    )

    # valores
    for barra, ratio_original, log_valor in zip(barras, ratio, ratio_log):
        ax.text(
            log_valor + (0.05 if log_valor >= 0 else -0.05),
            barra.get_y() + barra.get_height() / 2,
            f"{ratio_original:.3f}",
            va="center",
            ha="left" if log_valor >= 0 else "right",
            color=TEXTO,
            fontsize=12
        )

    ax.set_xticks([-3, -2, -1, 0, 1, 2, 3])
    ax.set_xticklabels(["8x", "4x", "2x", "1.0\n(balanced)", "2x", "4x", "8x"], color=TEXTO, fontsize=3)

    ax.set_yticks(list(y))
    ax.set_yticklabels(nomes, color=TEXTO, fontsize=3)

    ax.set_xlabel("Ratio Delta", color=TEXTO)

    _aplicar_estilo(ax, "Ratio Delta")
    _salvar(fig, "ratio.png")





# Entry point
def gerar_todos_graficos(resultados: list[dict], caminho_csv: str) -> None:
    plt.rcParams.update({"font.family": "monospace", "figure.facecolor": FUNDO,
                          "axes.facecolor": FUNDO2, "text.color": TEXTO})
    os.makedirs(RESULTS_DIR, exist_ok=True)  # garante pasta antes de qualquer save

    df = carregar_dados(caminho_csv)
    gerar_tabela(df)
    gerar_graficos(df)
    grafico_ranking_scores(resultados)
    grafico_ratio(resultados)


#Se quiser gerar os gráficos sem "refazer" os dados
if __name__ == "__main__":
    caminho_csv      = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_CSV        
    caminho_result   = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RESULTS_DIR, "resultados.csv")

    # Lê o CSV de resultados já calculados
    import csv
    resultados = []
    with open(caminho_result, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for campo in ("yt_score_medio", "tw_score_medio", "ratio_delta"):
                val = row.get(campo, "")
                row[campo] = float(val) if val else None
            row["yt_serie"] = []
            row["tw_serie"] = []
            resultados.append(row)
        
    gerar_todos_graficos(resultados, caminho_csv)