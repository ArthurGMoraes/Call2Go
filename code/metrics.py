"""
Funções principais:
  - calcular_intervalos(posts)      -> lista de Δt em dias
  - calcular_score_plataforma(data) -> score por plataforma em cada janela
  - calcular_ritmo_relativo(yt, tw) -> ratio Δt_yt / Δt_tw
  - analisar_criador(criador_data)  -> dict completo de métricas
"""

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Optional
from config import JANELA_DIAS


# Intervalos entre postagens
def calcular_intervalos(posts: list[dict]) -> list[float]:
    """
    Recebe lista de posts ordenada por 'publicado_em'.
    Retorna lista de Δt em dias entre postagens consecutivas.
    """
    if len(posts) < 2:
        return []

    datas = [p["publicado_em"] for p in posts]
    deltas = []
    for i in range(len(datas) - 1):
        diff = datas[i+1] - datas[i]
        deltas.append(diff.total_seconds() / 86400)
    return deltas


def resumo_intervalos(deltas: list[float]) -> dict:
    """Estatísticas descritivas dos intervalos."""
    if not deltas:
        return {"media": None, "mediana": None, "desvio": None, "n": 0}

    return {
        "media":   statistics.mean(deltas),
        "mediana": statistics.median(deltas),
        "desvio":  statistics.stdev(deltas) if len(deltas) > 1 else 0.0,
        "n":       len(deltas),
    }


# Score por plataforma (janela deslizante)
def _posts_na_janela(posts: list[dict], inicio: datetime, fim: datetime) -> list[dict]:
    """Filtra posts dentro de [inicio, fim)."""
    return [p for p in posts if inicio <= p["publicado_em"] < fim]


def _score_janela_yt(posts_janela: list[dict], subscribers: int) -> float:
    """
    score_yt = regularidade × avg_views/subscribers
    regularidade = 1 / (1 + σ_Δt)  — quanto menor o desvio, mais perto de 1
    """
    if not posts_janela or subscribers <= 0:
        return 0.0

    deltas = calcular_intervalos(posts_janela)
    desvio = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    regularidade = 1.0 / (1.0 + desvio)

    avg_views = statistics.mean(p["views"] for p in posts_janela)
    taxa_penetracao = avg_views/subscribers

    return regularidade * taxa_penetracao


def _score_janela_tw(posts_janela: list[dict], followers: int) -> float:
    """
    score_tw = regularidade × avg_views/followers
    regularidade = 1 / (1 + σ_Δt)  — quanto menor o desvio, mais perto de 1
    """
    if not posts_janela or followers <= 0:
        return 0.0

    deltas = calcular_intervalos(posts_janela)
    desvio = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    regularidade = 1.0 / (1.0 + desvio)

    avg_views = statistics.mean(p["views"] for p in posts_janela)
    taxa_penetracao = avg_views/followers

    return regularidade * taxa_penetracao


def calcular_serie_scores(
    posts: list[dict],
    audiencia: int,
    plataforma: str,
    data_inicio: Optional[datetime] = None,
    data_fim:    Optional[datetime] = None,
) -> list[dict]:
    """
    Gera série temporal de scores em janelas de JANELA_DIAS dias.
    Retorna lista de dicts: [{janela_inicio, janela_fim, score, n_posts}]
    """
    if not posts:
        return []

    data_inicio = data_inicio or posts[0]["publicado_em"]
    data_fim    = data_fim    or datetime.now(timezone.utc)

    serie = []
    cursor = data_inicio

    fn_score = _score_janela_yt if plataforma == "youtube" else _score_janela_tw

    while cursor < data_fim:
        fim_janela  = cursor + timedelta(days=JANELA_DIAS)
        posts_jan   = _posts_na_janela(posts, cursor, fim_janela)
        score       = fn_score(posts_jan, audiencia)

        serie.append({
            "janela_inicio": cursor,
            "janela_fim":    fim_janela,
            "score":         score,
            "n_posts":       len(posts_jan),
        })
        cursor = fim_janela

    return serie


# Ratio 
def calcular_ritmo_relativo(delta_medio_yt: Optional[float], delta_medio_tw: Optional[float]) -> Optional[float]:
    """
    ratio = Δt_yt / Δt_tw
      > 1 → mais ativo na Twitch (publica com menos frequência no YT)
      < 1 → mais ativo no YT
      ≈ 1 → cadência equilibrada entre plataformas
    Retorna None se algum dos valores for inválido.
    """
    if delta_medio_yt is None or delta_medio_tw is None:
        return None
    if delta_medio_tw == 0:
        return None
    return delta_medio_yt / delta_medio_tw


# Análise por criador
def analisar_criador(criador: dict) -> dict:
    """
    Recebe o dict retornado por collector.coletar_criador() e
    retorna dict completo com todas as métricas calculadas.
    """
    nome    = criador["nome"]
    yt_data = criador.get("youtube")
    tw_data = criador.get("twitch")

    resultado = {
        "nome":           nome,
        "jogo":           criador.get("jogo"),
        "infantil":       criador.get("infantil"),
        # YouTube
        "yt_subscribers": None,
        "yt_n_posts":     None,
        "yt_delta_medio": None,
        "yt_delta_desvio":None,
        "yt_score_medio": None,
        "yt_serie":       [],
        # Twitch
        "tw_followers":   None,
        "tw_n_posts":     None,
        "tw_delta_medio": None,
        "tw_delta_desvio":None,
        "tw_score_medio": None,
        "tw_serie":       [],
        # Cross-platform
        "ratio_delta":    None,
        "perfil":         "sem dados",
    }

    # YouTube
    if yt_data and yt_data.get("posts"):
        posts_yt = yt_data["posts"]
        subs     = yt_data["subscribers"]
        deltas   = calcular_intervalos(posts_yt)
        res_int  = resumo_intervalos(deltas)
        serie_yt = calcular_serie_scores(posts_yt, subs, "youtube")
        scores   = [s["score"] for s in serie_yt if s["n_posts"] > 0]

        resultado.update({
            "yt_subscribers": subs,
            "yt_n_posts":     len(posts_yt),
            "yt_delta_medio": res_int["media"],
            "yt_delta_desvio":res_int["desvio"],
            "yt_score_medio": statistics.mean(scores) if scores else 0.0,
            "yt_serie":       serie_yt,
        })

    # Twitch 
    if tw_data and tw_data.get("posts"):
        posts_tw  = tw_data["posts"]
        followers = tw_data["followers"]
        deltas    = calcular_intervalos(posts_tw)
        res_int   = resumo_intervalos(deltas)
        serie_tw  = calcular_serie_scores(posts_tw, followers, "twitch")
        scores    = [s["score"] for s in serie_tw if s["n_posts"] > 0]

        resultado.update({
            "tw_followers":   followers,
            "tw_n_posts":     len(posts_tw),
            "tw_delta_medio": res_int["media"],
            "tw_delta_desvio":res_int["desvio"],
            "tw_score_medio": statistics.mean(scores) if scores else 0.0,
            "tw_serie":       serie_tw,
        })

    #  Cross-platform 
    if resultado["yt_delta_medio"] and resultado["tw_delta_medio"]:
        ratio = calcular_ritmo_relativo(
            resultado["yt_delta_medio"],
            resultado["tw_delta_medio"],
        )
        resultado.update({
            "ratio_delta":    ratio,
        })

    #Profile
    resultado["perfil"] = _classificar_perfil(resultado)

    return resultado


def _classificar_perfil(r: dict) -> str:
    #Classifica o criador em um dos 3 profiles.
    tem_yt = r["yt_score_medio"] is not None and r["yt_score_medio"] > 0
    tem_tw = r["tw_score_medio"] is not None and r["tw_score_medio"] > 0

    if not tem_yt and not tem_tw:
        return "dormente"
    if tem_yt and not tem_tw:
        return "yt-only"
    if tem_tw and not tem_yt:
        return "twitch-only"
    if tem_tw and tem_yt:
        return "biplataforma"
