# Estação ADS-B com alertas no Telegram

🇧🇷 Português · [🇬🇧 English](README.en.md)

Guia e código para montar uma estação que recebe sinais de aeronaves (ADS-B, 1090 MHz) com um RTL-SDR e um Raspberry Pi, alimenta o ADS-B Exchange e envia alertas no Telegram quando uma aeronave da sua lista é detectada.

**Guia completo (PDF):** [Português](docs/GUIA_ESTACAO_ADSB.pdf) · [English](docs/ADSB_STATION_GUIDE_EN.pdf)

## Hardware usado

- Raspberry Pi 3 (1 GB)
- RTL-SDR V3 (ou clone com chip RTL2832U)
- Filtro passa-faixa 1090 MHz
- Antena para 1090 MHz

## Como funciona

```
Antena -> Filtro 1090 MHz -> RTL-SDR -> Raspberry Pi
                                         |-- readsb (gera /run/readsb/aircraft.json)
                                         |-- tar1090 (mapa local)
                                         |-- adsbexchange-feed
                                         '-- radar-bot (alertas no Telegram)
```

## Arquivos

| Arquivo | Função |
|---|---|
| `radar_bot.py` | Bot: lê o `aircraft.json` e envia alertas |
| `aeronaves.example.json` | Exemplo da lista de aeronaves (dados fictícios) |
| `.env.example` | Modelo do arquivo de credenciais |
| `radar-bot.service` | Serviço systemd |

## Instalação rápida do bot

```bash
mkdir -p ~/radar_bot && cd ~/radar_bot
# copie os arquivos deste repositório para esta pasta
cp aeronaves.example.json aeronaves.json   # edite com as suas aeronaves
cp .env.example .env && chmod 600 .env     # preencha TG_TOKEN e TG_CHAT_ID
python3 -m py_compile radar_bot.py && python3 -m json.tool aeronaves.json > /dev/null
sudo cp radar-bot.service /etc/systemd/system/   # ajuste User e caminhos antes
sudo systemctl daemon-reload && sudo systemctl enable --now radar-bot
```

Os passos completos (readsb, tar1090, feed do ADS-B Exchange, criação do bot) estão no PDF.

## Idioma das mensagens

Defina `TG_LANG` no `.env`: `pt` (padrão) ou `en`. Os logs do bot continuam em português.

## Formato do `aeronaves.json`

```json
[
  {"nome": "NOME DE EXIBIÇÃO", "callsign": "PPXXX", "hex": ["AAAAAA", "BBBBBB"]}
]
```

O bot recarrega o arquivo sozinho a cada 5 minutos, sem reiniciar.

## Segurança

- Token e chat_id ficam só no `.env`, que o `.gitignore` bloqueia.
- Nunca publique o `.env` nem a sua lista real de aeronaves.
- Se um token vazar, revogue no @BotFather (`/mybots` -> API Token -> Revoke).
