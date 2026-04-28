"""
Analisador de Influencers por Plataforma e Jogo
================================================
Lê um CSV com dados de influencers e gera:
  1. Gráfico: Plataforma x Conteúdo infantil
  2. Tabela de influencers formatada

Formato esperado do CSV:
  nome_influencer; link_youtube; link_twitch; link_discord; nome_jogo; infantil
  (link_youtube, link_twitch e link_discord são opcionais)
  (infantil: "s" ou "n" baseado na classificação indicativa)
"""

import sys
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ── Configuração ──────────────────────────────────────────────────────────────

ARQUIVO_CSV = "../data/influencers.csv"   # altere aqui ou passe como argumento

PLATAFORMAS = {
    "YouTube": "link_youtube",
    "Twitch":  "link_twitch",
    "Discord": "link_discord",
}

CORES_PLATAFORMA = {
    "YouTube": "#FF4444",
    "Twitch":  "#9146FF",
    "Discord": "#5865F2",
}

PALETTE_JOGOS = [
    "#00C9A7", "#FF6B6B", "#FFC300", "#4FACFE",
    "#A8FF78", "#F7971E", "#C471ED", "#12C2E9",
]

FUNDO     = "#0F0F14"
FUNDO2    = "#1A1A24"
TEXTO     = "#E8E8F0"
DESTAQUE  = "#C8FF00"
BORDA     = "#2E2E42"

# ── Leitura e validação ───────────────────────────────────────────────────────

def carregar_dados(caminho: str) -> pd.DataFrame:
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        sys.exit(1)

    df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.lower()

    colunas_obrigatorias = {"nome_influencer", "nome_jogo"}
    colunas_faltando = colunas_obrigatorias - set(df.columns)
    if colunas_faltando:
        print(f"[ERRO] Colunas obrigatórias ausentes no CSV: {colunas_faltando}")
        sys.exit(1)

    # Garantir colunas opcionais
    for col in PLATAFORMAS.values():
        if col not in df.columns:
            df[col] = ""

    df = df.fillna("").map(str.strip)
    df["nome_influencer"] = df["nome_influencer"].str.strip()
    df["nome_jogo"]       = df["nome_jogo"].str.strip()
    df = df[df["nome_influencer"].ne("")].reset_index(drop=True)

    # Coluna opcional infantil (s/n -> bool)
    if "infantil" not in df.columns:
        df["infantil"] = "n"
    df["infantil"] = df["infantil"].str.lower().map(lambda v: v == "s")

    # Colunas booleanas de presença em cada plataforma
    for nome, col in PLATAFORMAS.items():
        df[f"tem_{nome}"] = df[col].ne("").astype(int)

    return df

# ── Tabela no terminal ────────────────────────────────────────────────────────

def imprimir_tabela(df: pd.DataFrame) -> None:
    larguras = {
        "influencer": max(20, df["nome_influencer"].str.len().max() + 2),
        "jogo":       max(15, df["nome_jogo"].str.len().max() + 2),
        "youtube":    9,
        "twitch":     8,
        "discord":    9,
        "infantil":   10,
    }

    separador = (
        "+"
        + "-" * larguras["influencer"]
        + "+"
        + "-" * larguras["jogo"]
        + "+"
        + "-" * larguras["youtube"]
        + "+"
        + "-" * larguras["twitch"]
        + "+"
        + "-" * larguras["discord"]
        + "+"
        + "-" * larguras["infantil"]
        + "+"
    )

    def linha(influencer, jogo, yt, tw, dc, inf):
        return (
            f"| {influencer:<{larguras['influencer']-2}} "
            f"| {jogo:<{larguras['jogo']-2}} "
            f"| {yt:^{larguras['youtube']-2}} "
            f"| {tw:^{larguras['twitch']-2}} "
            f"| {dc:^{larguras['discord']-2}} "
            f"| {inf:^{larguras['infantil']-2}} |"
        )

    print("\n" + "═" * len(separador))
    print("  INFLUENCERS — PLATAFORMAS & JOGOS")
    print("═" * len(separador))
    print(separador)
    print(linha("Influencer", "Jogo", "YouTube", "Twitch", "Discord", "Infantil"))
    print(separador.replace("-", "="))

    for _, row in df.iterrows():
        yt  = "✔" if row["tem_YouTube"] else "·"
        tw  = "✔" if row["tem_Twitch"]  else "·"
        dc  = "✔" if row["tem_Discord"] else "·"
        inf = "✔" if row["infantil"]    else "·"
        print(linha(row["nome_influencer"], row["nome_jogo"], yt, tw, dc, inf))

    print(separador)

    total_yt  = df["tem_YouTube"].sum()
    total_tw  = df["tem_Twitch"].sum()
    total_dc  = df["tem_Discord"].sum()
    total_inf = df["infantil"].sum()
    print(linha("TOTAL", "", str(total_yt), str(total_tw), str(total_dc), str(total_inf)))
    print(separador)
    print(f"  Total de influencers: {len(df)}  |  Infantis: {total_inf}  |  Adultos: {len(df) - total_inf}\n")

# ── Gráficos ──────────────────────────────────────────────────────────────────

def aplicar_estilo_eixo(ax, titulo: str) -> None:
    ax.set_facecolor(FUNDO2)
    ax.tick_params(colors=TEXTO, labelsize=10)
    ax.set_title(titulo, color=DESTAQUE, fontsize=13, fontweight="bold", pad=14)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDA)
    ax.title.set_fontfamily("monospace")


def grafico_por_jogo(ax, df: pd.DataFrame) -> None:
    jogos = df["nome_jogo"].unique()
    x     = range(len(jogos))
    n     = len(PLATAFORMAS)
    largura_barra = 0.25

    plataformas = list(PLATAFORMAS.keys())

    for i, plataforma in enumerate(plataformas):
        valores = [
            df[df["nome_jogo"] == jogo][f"tem_{plataforma}"].sum()
            for jogo in jogos
        ]
        offset = (i - n / 2 + 0.5) * largura_barra
        barras = ax.bar(
            [xi + offset for xi in x], valores,
            width=largura_barra,
            color=CORES_PLATAFORMA[plataforma],
            label=plataforma,
            edgecolor=FUNDO, linewidth=1.2
        )
        for barra, v in zip(barras, valores):
            if v > 0:
                ax.text(
                    barra.get_x() + barra.get_width() / 2,
                    barra.get_height() + 0.05,
                    str(v),
                    ha="center", va="bottom",
                    color=TEXTO, fontsize=8
                )

    ax.set_xticks(list(x))
    ax.set_xticklabels(jogos, rotation=25, ha="right", color=TEXTO, fontsize=9)
    ax.set_ylabel("Nº de Influencers", color=TEXTO, fontsize=10)
    ax.yaxis.label.set_color(TEXTO)
    max_val = max(
        df[df["nome_jogo"] == jogo][f"tem_{p}"].sum()
        for jogo in jogos for p in plataformas
    )
    ax.set_ylim(0, max_val * 1.35)
    ax.set_yticks(range(0, max_val + 2))
    ax.yaxis.grid(True, color=BORDA, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    legenda = ax.legend(
        facecolor=FUNDO, edgecolor=BORDA,
        labelcolor=TEXTO, fontsize=9,
        loc="upper right"
    )

    aplicar_estilo_eixo(ax, "Influencers por Jogo e Plataforma")


def grafico_plataforma_infantil(ax, df: pd.DataFrame) -> None:
    plataformas = list(PLATAFORMAS.keys())
    x = range(len(plataformas))

    categorias = [
        ("Adulto",   False, "#4B9CD3"),
        ("Infantil", True,  "#FFD166"),
    ]

    barras_acumuladas = [0] * len(plataformas)

    for label, flag, cor in categorias:
        valores = [
            df[(df[f"tem_{p}"] == 1) & (df["infantil"] == flag)].shape[0]
            for p in plataformas
        ]
        barras = ax.bar(
            list(x), valores,
            width=0.5,
            bottom=barras_acumuladas,
            color=cor,
            label=label,
            edgecolor=FUNDO, linewidth=1.0
        )
        # Anotação no centro de cada segmento
        for barra, v, base in zip(barras, valores, barras_acumuladas):
            if v > 0:
                ax.text(
                    barra.get_x() + barra.get_width() / 2,
                    base + v / 2,
                    str(v),
                    ha="center", va="center",
                    color=FUNDO, fontsize=11, fontweight="bold"
                )
        barras_acumuladas = [a + v for a, v in zip(barras_acumuladas, valores)]

    # Total no topo de cada barra
    for xi, total in zip(x, barras_acumuladas):
        ax.text(
            xi, total + 0.15, str(total),
            ha="center", va="bottom",
            color=TEXTO, fontsize=10, fontweight="bold"
        )

    max_total = max(barras_acumuladas) if barras_acumuladas else 1
    ax.set_ylim(0, max_total * 1.25)
    ax.set_yticks(range(0, max_total + 2))
    ax.set_xticks(list(x))
    ax.set_xticklabels(plataformas)
    for tick, plataforma in zip(ax.get_xticklabels(), plataformas):
        tick.set_color(CORES_PLATAFORMA[plataforma])
        tick.set_fontweight("bold")
        tick.set_fontsize(11)

    ax.set_ylabel("Nº de Influencers", color=TEXTO, fontsize=10)
    ax.yaxis.label.set_color(TEXTO)
    ax.yaxis.grid(True, color=BORDA, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    ax.legend(
        facecolor=FUNDO, edgecolor=BORDA,
        labelcolor=TEXTO, fontsize=9,
        loc="upper right"
    )
    aplicar_estilo_eixo(ax, "Plataforma × Conteúdo Infantil")


def gerar_tabela(df: pd.DataFrame, salvar_como: str = "../results/tabela_influencers.png") -> None:
    plt.rcParams.update({
        "font.family": "monospace",
        "figure.facecolor": FUNDO,
        "text.color": TEXTO,
    })

    def link_para_icone(url: str) -> str:
        return "✔" if url.strip() else "·"

    def infantil_label(val) -> str:
        return "Sim" if val else "Não"

    freq = df["nome_jogo"].value_counts()
    df["freq_jogo"] = df["nome_jogo"].map(freq)

    df = df.sort_values(
        by=["freq_jogo", "infantil", "nome_jogo", "nome_influencer"],
        ascending=[False, False, True, True]
    ).drop(columns="freq_jogo")

    linhas = []
    for _, row in df.iterrows():
        linhas.append([
            row["nome_influencer"],
            row["nome_jogo"],
            link_para_icone(row.get("link_youtube", "")),
            link_para_icone(row.get("link_twitch",  "")),
            link_para_icone(row.get("link_discord", "")),
            infantil_label(row["infantil"]),
        ])

    colunas = ["Influencer", "Jogo", "YouTube", "Twitch", "Discord", "Infantil"]

    n_linhas = len(linhas)
    altura_fig = max(3.5, 0.45 * n_linhas + 1.5)
    fig, ax = plt.subplots(figsize=(13, altura_fig), facecolor=FUNDO)
    ax.set_facecolor(FUNDO)
    ax.axis("off")

    tabela = ax.table(
        cellText=linhas,
        colLabels=colunas,
        loc="center",
        cellLoc="center",
    )
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(10)
    tabela.scale(1, 1.6)

    # Larguras relativas das colunas
    col_widths = [0.26, 0.18, 0.10, 0.10, 0.10, 0.10]
    for (row_idx, col_idx), cell in tabela.get_celld().items():
        cell.set_width(col_widths[col_idx])
        cell.set_edgecolor(BORDA)
        cell.set_linewidth(0.5)

        if row_idx == 0:
            # Cabeçalho
            cell.set_facecolor(DESTAQUE)
            cell.set_text_props(color=FUNDO, fontweight="bold", fontsize=10)
        elif row_idx % 2 == 0:
            cell.set_facecolor("#16161f")
            cell.set_text_props(color=TEXTO)
        else:
            cell.set_facecolor(FUNDO2)
            cell.set_text_props(color=TEXTO)

        # Alinhar à esquerda colunas de texto
        if col_idx in (0, 1):
            cell.set_text_props(ha="left")
            cell.PAD = 0.04

        # Colorir ✔ / · nas plataformas
        if row_idx > 0 and col_idx in (2, 3, 4):
            txt = linhas[row_idx - 1][col_idx]
            cell.set_text_props(color="#C8FF00" if txt == "✔" else "#555566")

        # Colorir coluna Infantil
        if row_idx > 0 and col_idx == 5:
            txt = linhas[row_idx - 1][5]
            cell.set_text_props(color="#FFD166" if txt == "Sim" else TEXTO)

    fig.suptitle(
        "LISTA DE INFLUENCERS",
        color=DESTAQUE, fontsize=14, fontweight="bold",
        fontfamily="monospace", y=0.98
    )
    fig.text(
        0.5, 0.01,
        f"Total: {len(df)}  |  Infantis: {df['infantil'].sum()}  |  Adultos: {(~df['infantil']).sum()}",
        ha="center", color=TEXTO, fontsize=9, alpha=0.6
    )

    plt.savefig(salvar_como, dpi=150, bbox_inches="tight", facecolor=FUNDO)
    print(f"[OK] Tabela salva em: {salvar_como}")


def gerar_graficos(df: pd.DataFrame, salvar_como: str = "../results/relatorio_plataformas.png") -> None:
    plt.rcParams.update({
        "font.family": "monospace",
        "figure.facecolor": FUNDO,
        "axes.facecolor":   FUNDO2,
        "text.color":       TEXTO,
    })

    fig = plt.figure(figsize=(20, 12), facecolor=FUNDO)
    fig.suptitle(
        "DASHBOARD DE INFLUENCERS",
        color=DESTAQUE, fontsize=18, fontweight="bold",
        fontfamily="monospace", y=0.98
    )

    gs = GridSpec(1, 2, figure=fig, wspace=0.35, hspace=0.45,
                  left=0.07, right=0.97, top=0.91, bottom=0.08)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    grafico_por_jogo(ax2, df)
    grafico_plataforma_infantil(ax1, df)

    # Rodapé
    fig.text(
        0.5, 0.02,
        f"Total de influencers analisados: {len(df)}",
        ha="center", color=TEXTO, fontsize=9, alpha=0.6
    )

    plt.savefig(salvar_como, dpi=150, bbox_inches="tight", facecolor=FUNDO)
    print(f"[OK] Gráfico salvo em: {salvar_como}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_CSV

    df = carregar_dados(caminho)

    imprimir_tabela(df)
    gerar_tabela(df)
    gerar_graficos(df)


if __name__ == "__main__":
    main()