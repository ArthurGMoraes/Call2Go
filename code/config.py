"""
Configuração central do projeto 
Sem .env: as chaves são lidas de variáveis de ambiente do sistema.
Requer variáveis de ambiente:
  YOUTUBE_API_KEY
  TWITCH_CLIENT_ID
  TWITCH_CLIENT_SECRET
"""

from dotenv import load_dotenv
load_dotenv() 

import os
YOUTUBE_API_KEY      = os.environ.get("YOUTUBE_API_KEY", "")
TWITCH_CLIENT_ID     = os.environ.get("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "")

#Caminhos

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
ARQUIVO_CSV = os.path.join(DATA_DIR, "influencers.csv")

# Parâmetros do algoritmo 

JANELA_DIAS        = 7    # tamanho da janela deslizante em dias
MAX_VIDEOS_YT      = 90    # máximo de vídeos buscados por canal no YT
MAX_STREAMS_TWITCH = 90   # máximo de VODs/streams buscados por canal na Twitch

# Cores para gráficos
FUNDO    = "#FFFFFF"
FUNDO2   = "#FFFFFFB8"
TEXTO    = "#000000"
DESTAQUE = "#C8FF00"
BORDA    = "#2E2E42"

CORES_PLATAFORMA = {
    "YouTube": "#FF4444",
    "Twitch":  "#9146FF",
    "Discord": "#5865F2",
}

PALETTE_JOGOS = [
    "#00C9A7", "#FF6B6B", "#FFC300", "#4FACFE",
    "#A8FF78", "#F7971E", "#C471ED", "#12C2E9",
]

PLATAFORMAS = {
    "YouTube": "link_youtube",
    "Twitch":  "link_twitch",
    "Discord": "link_discord",
}

# CSV resultados
COLUNAS_CSV = [
    "nome", "jogo", "infantil",
    "yt_subscribers", "yt_n_posts", "yt_delta_medio", "yt_delta_desvio", "yt_score_medio",
    "tw_followers",   "tw_n_posts", "tw_delta_medio", "tw_delta_desvio", "tw_score_medio",
    "ratio_delta", "perfil", "flow",
]
