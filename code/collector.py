"""
collector.py — Coleta de dados via APIs do YouTube e Twitch
============================================================
Funções:
  - extrair_channel_id_yt(url)  → ID do canal YouTube
  - extrair_username_twitch(url) → username Twitch
  - buscar_token_twitch()        → OAuth token client_credentials
  - coletar_youtube(channel_id)  → dict com metadados + lista de vídeos
  - coletar_twitch(username)     → dict com metadados + lista de streams
  - coletar_criador(row)         → dict unificado por criador

Todas as funções de coleta retornam None em caso de erro,
para que o pipeline continue com os demais criadores.
"""

import re
import time
import requests
from datetime import datetime, timezone
from config import (
    YOUTUBE_API_KEY, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET,
    MAX_VIDEOS_YT, MAX_STREAMS_TWITCH,
)

# Helpers de URL
def extrair_channel_id_yt(url: str) -> str | None:
    """
    Extrai o identificador do canal YouTube a partir de diferentes formatos de URL:
      - /channel/UCxxxx  → retorna o ID direto
      - /@handle ou /user/nome ou /c/nome → retorna o handle/nome (resolve depois)
    """
    url = url.strip().rstrip("/")
    if not url:
        return None

    # ID direto: /channel/UCxxxxxxxxxxxxxxxxxxxxxxxx
    m = re.search(r"/channel/(UC[\w-]{22})", url)
    if m:
        return m.group(1)

    # Handle: /@NomeDoCanal
    m = re.search(r"/@([\w.-]+)", url)
    if m:
        return f"@{m.group(1)}"

    # /user/nome ou /c/nome
    m = re.search(r"/(?:user|c)/([\w.-]+)", url)
    if m:
        return m.group(1)

    # URL base do canal (youtube.com/NomeCanal)
    m = re.search(r"youtube\.com/([\w.-]+)$", url)
    if m:
        return m.group(1)

    return None


def extrair_username_twitch(url: str) -> str | None:
    """Extrai o username da Twitch a partir de twitch.tv/username."""
    url = url.strip().rstrip("/")
    if not url:
        return None
    m = re.search(r"twitch\.tv/([\w]+)", url)
    return m.group(1) if m else None


# Autenticação Twitch
_twitch_token: str | None = None
_twitch_token_expira: float = 0.0

def buscar_token_twitch() -> str | None:
    """Obtém token OAuth client_credentials da Twitch (com cache)."""
    global _twitch_token, _twitch_token_expira

    if _twitch_token and time.time() < _twitch_token_expira - 60:
        return _twitch_token

    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        print("[AVISO] Credenciais da Twitch não configuradas.")
        return None

    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id":     TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type":    "client_credentials",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[ERRO] Token Twitch: {resp.status_code} {resp.text}")
        return None

    data = resp.json()
    _twitch_token = data["access_token"]
    _twitch_token_expira = time.time() + data.get("expires_in", 3600)
    return _twitch_token


# Coleta YouTube
YT_BASE = "https://www.googleapis.com/youtube/v3"

def _resolver_channel_id(identificador: str) -> str | None:
    """
    Se o identificador não for um UC..., usa a Search API para resolver.
    Retorna o channel_id real ou None.
    """
    if identificador.startswith("UC") and len(identificador) == 24:
        return identificador

    resp = requests.get(
        f"{YT_BASE}/search",
        params={
            "key":  YOUTUBE_API_KEY,
            "q":    identificador.lstrip("@"),
            "type": "channel",
            "part": "snippet",
            "maxResults": 1,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[ERRO] Resolução de canal YT '{identificador}': {resp.status_code}")
        return None

    items = resp.json().get("items", [])
    if not items:
        print(f"[AVISO] Canal YT não encontrado: '{identificador}'")
        return None

    return items[0]["snippet"]["channelId"]


def _buscar_uploads_playlist(channel_id: str) -> str | None:
    """Retorna o ID da playlist 'uploads' de um canal."""
    resp = requests.get(
        f"{YT_BASE}/channels",
        params={
            "key":  YOUTUBE_API_KEY,
            "id":   channel_id,
            "part": "contentDetails,statistics",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        return None

    items = resp.json().get("items", [])
    if not items:
        return None

    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def coletar_youtube(url: str) -> dict | None:
    """
    Coleta dados do canal YouTube:
      - subscribers, total_views
      - lista de vídeos: [{publicado_em, views, likes}]
    """
    if not YOUTUBE_API_KEY:
        print("[AVISO] YOUTUBE_API_KEY não configurada.")
        return None

    identificador = extrair_channel_id_yt(url)
    if not identificador:
        return None

    channel_id = _resolver_channel_id(identificador)
    if not channel_id:
        return None

    # Metadados do canal
    resp_ch = requests.get(
        f"{YT_BASE}/channels",
        params={
            "key":  YOUTUBE_API_KEY,
            "id":   channel_id,
            "part": "statistics",
        },
        timeout=10,
    )
    if resp_ch.status_code != 200:
        print(f"[ERRO] Metadados YT {channel_id}: {resp_ch.status_code}")
        return None

    items = resp_ch.json().get("items", [])
    if not items:
        return None

    stats = items[0]["statistics"]
    subscribers  = int(stats.get("subscriberCount", 0))
    total_views  = int(stats.get("viewCount", 0))

    # Playlist de uploads
    playlist_id = _buscar_uploads_playlist(channel_id)
    if not playlist_id:
        return None

    # Vídeos (paginação)
    videos = []
    page_token = None
    while len(videos) < MAX_VIDEOS_YT:
        params = {
            "key":        YOUTUBE_API_KEY,
            "playlistId": playlist_id,
            "part":       "contentDetails",
            "maxResults": min(50, MAX_VIDEOS_YT - len(videos)),
        }
        if page_token:
            params["pageToken"] = page_token

        resp_pl = requests.get(f"{YT_BASE}/playlistItems", params=params, timeout=10)
        if resp_pl.status_code != 200:
            break

        data = resp_pl.json()
        ids_video = [
            it["contentDetails"]["videoId"]
            for it in data.get("items", [])
        ]

        if not ids_video:
            break

        # Detalhes de cada vídeo (views, likes, data)
        resp_vid = requests.get(
            f"{YT_BASE}/videos",
            params={
                "key":  YOUTUBE_API_KEY,
                "id":   ",".join(ids_video),
                "part": "statistics,snippet",
            },
            timeout=10,
        )
        if resp_vid.status_code == 200:
            for v in resp_vid.json().get("items", []):
                s = v["statistics"]
                publicado = v["snippet"].get("publishedAt", "")
                try:
                    dt = datetime.fromisoformat(publicado.replace("Z", "+00:00"))
                except ValueError:
                    continue
                videos.append({
                    "publicado_em": dt,
                    "views":        int(s.get("viewCount",  0)),
                    "likes":        int(s.get("likeCount",  0)),
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return {
        "platform":     "youtube",
        "channel_id":   channel_id,
        "subscribers":  subscribers,
        "total_views":  total_views,
        "posts":        sorted(videos, key=lambda x: x["publicado_em"]),
    }


# Coleta Twitch
TWITCH_BASE = "https://api.twitch.tv/helix"

def coletar_twitch(url: str) -> dict | None:
    """
    Coleta dados do canal Twitch:
      - followers
      - lista de streams/VODs: [{publicado_em, views}]
    """
    token = buscar_token_twitch()
    if not token:
        return None

    username = extrair_username_twitch(url)
    if not username:
        return None

    headers = {
        "Client-ID":    TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    # ID do usuário + followers
    resp_user = requests.get(
        f"{TWITCH_BASE}/users",
        params={"login": username},
        headers=headers,
        timeout=10,
    )
    if resp_user.status_code != 200 or not resp_user.json().get("data"):
        print(f"[ERRO] Usuário Twitch '{username}': {resp_user.status_code}")
        return None

    user_data  = resp_user.json()["data"][0]
    user_id    = user_data["id"]

    # Followers (endpoint separado)
    resp_fol = requests.get(
        f"{TWITCH_BASE}/channels/followers",
        params={"broadcaster_id": user_id, "first": 1},
        headers=headers,
        timeout=10,
    )
    followers = 0
    if resp_fol.status_code == 200:
        followers = resp_fol.json().get("total", 0)

    # VODs (streams gravados)
    streams = []
    cursor  = None
    while len(streams) < MAX_STREAMS_TWITCH:
        params = {
            "user_id": user_id,
            "type":    "archive",
            "first":   min(100, MAX_STREAMS_TWITCH - len(streams)),
        }
        if cursor:
            params["after"] = cursor

        resp_vod = requests.get(
            f"{TWITCH_BASE}/videos",
            params=params,
            headers=headers,
            timeout=10,
        )
        if resp_vod.status_code != 200:
            break

        data = resp_vod.json()
        for v in data.get("data", []):
            try:
                dt = datetime.fromisoformat(v["created_at"].replace("Z", "+00:00"))
            except ValueError:
                continue
            streams.append({
                "publicado_em": dt,
                "views":        int(v.get("view_count", 0)),
            })

        cursor = data.get("pagination", {}).get("cursor")
        if not cursor:
            break

    return {
        "platform":  "twitch",
        "username":  username,
        "followers": followers,
        "posts":     sorted(streams, key=lambda x: x["publicado_em"]),
    }


# Coleta por criador
def coletar_criador(row: dict) -> dict:
    """
    Recebe uma linha do CSV e retorna um dict com dados de ambas as plataformas.
    Campos ausentes ficam como None.
    """
    nome = row.get("nome_influencer", "").strip()
    print(f"[→] Coletando: {nome}")

    yt_url = row.get("link_youtube", "").strip()
    tw_url = row.get("link_twitch",  "").strip()

    yt_data = coletar_youtube(yt_url) if yt_url else None
    tw_data = coletar_twitch(tw_url)  if tw_url else None

    return {
        "nome":     nome,
        "jogo":     row.get("nome_jogo", "").strip(),
        "infantil": row.get("infantil", "n").strip().lower() == "s",
        "youtube":  yt_data,
        "twitch":   tw_data,
    }
