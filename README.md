# Call2Go

Analisa a relação cross-platform (YouTube <-> Twitch) de criadores de conteúdo,
calculando ritmo de postagem e score de popularidade por plataforma

---

## Estrutura do projeto

```
Call2Go/
├── src/
|   ├── config.py      <- parâmetros e chaves de API
|   ├── collector.py   <- coleta YouTube + Twitch
|   ├── metrics.py     <- cálculo de ritmo e score
|   ├── charts.py      <- geração de gráficos
|   └── main.py        <- pipeline principal
├── data/
│   └── influencers.csv          <- seu CSV de entrada
├── results/                     <- saídas geradas automaticamente
└── ├── ranking_scores.png
    ├── relatorio_plataformas.png
    ├── resultados.csv
    └── tabela_influencers.csv

```

---

## Configuração

### 1. Instalar dependências

```bash
pip install requests pandas matplotlib
```

### 2. Configurar credenciais de API
Crie um arquivo .env com as keys na root do projeto
OU
Exporte as variáveis de ambiente antes de rodar:

```bash
export YOUTUBE_API_KEY="SUA_CHAVE_YOUTUBE"
export TWITCH_CLIENT_ID="SEU_CLIENT_ID_TWITCH"
export TWITCH_CLIENT_SECRET="SEU_CLIENT_SECRET_TWITCH"
```

**Como obter as chaves:**
- **YouTube**: [console.developers.google.com](https://console.developers.google.com) -> crie um projeto -> ative "YouTube Data API v3" -> Credenciais -> API Key
- **Twitch**: [dev.twitch.tv/console](https://dev.twitch.tv/console) -> Register Your Application -> Client ID + Client Secret

### 3. Formato do CSV

```
nome_influencer;link_youtube;link_twitch;link_discord;nome_jogo;infantil
Exemplo: Cellbit;https://www.youtube.com/@CellbitLives;https://www.twitch.tv/cellbit;;Variado;n
```

- Separador: `;`
- `link_twitch` e `link_youtube` são opcionais
- `infantil`: `s` ou `n`

---

## Execução

```bash
cd src/
python main.py                          # usa data/influencers.csv por padrão
python main.py ../data/meu_arquivo.csv  # CSV customizado
```

---

## Saídas

### `resultados.csv`
Tabela com uma linha por criador contendo:

| Campo            | Descrição                                      |
|------------------|------------------------------------------------|
| `yt_score_medio` | Score médio do YT ao longo das janelas         |
| `tw_score_medio` | Score médio da Twitch ao longo das janelas     |
| `yt_delta_medio` | Intervalo médio entre uploads (dias)           |
| `tw_delta_medio` | Intervalo médio entre lives (dias)             |
| `ratio_delta`*   | `Δt_yt / Δt_tw` — equilíbrio de cadência       |
| `perfil`         | Classificação do criador (ver abaixo)          |

*ratio>1 = mais presença na twitch, ratio<1 = mais presença no yt e ratio = 1 equilíbrio

### Perfis possíveis

| Perfil                    | Significado                                        |
|---------------------------|----------------------------------------------------|
| `yt-only`                 | Só tem dados relevantes no YouTube                 |
| `twitch-only`             | Só tem dados relevantes na Twitch                  |
| `biplatforma`             | Presente nas duas, mas sem correlação entre elas   |
| `dormente`                | Scores muito baixos ou sem dados                   |

### Gráficos

- **ranking_scores.png** — barras comparando score YT vs Twitch por criador
- **relatorio_plataformas.png** - barras comparando a presença de criadores por plataforma e tipo de conteúdo

---

## Parâmetros ajustáveis (`config.py`)

| Parâmetro            | Padrão | Descrição                              |
|----------------------|--------|----------------------------------------|
| `JANELA_DIAS`        | 7      | Tamanho da janela deslizante (dias)    |
| `MAX_VIDEOS_YT`      | 90     | Máximo de vídeos buscados por canal    |
| `MAX_STREAMS_TWITCH` | 90     | Máximo de VODs buscados por canal      |

---

## Notas sobre normalização
Views no YouTube (acumulado) e viewers na Twitch (simultâneo) são grandezas diferentes.
O `score_tw` divide o avg_viewers por `log10(followers)` antes de compor o score,
tornando a comparação mais justa entre plataformas.
