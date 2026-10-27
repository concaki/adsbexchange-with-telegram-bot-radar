# ADS-B Station with Telegram Alerts

[🇧🇷 Português](README.md) · 🇬🇧 English

Guide and code to build a station that receives aircraft signals (ADS-B, 1090 MHz) with an RTL-SDR and a Raspberry Pi, feeds ADS-B Exchange, and sends Telegram alerts when an aircraft from your list is detected.

**Full guide (PDF):** [English](docs/ADSB_STATION_GUIDE_EN.pdf) · [Português](docs/GUIA_ESTACAO_ADSB.pdf)

## Hardware used

- Raspberry Pi 3 (1 GB)
- RTL-SDR V3 (or a clone with an RTL2832U chip)
- 1090 MHz band-pass filter
- 1090 MHz antenna

## How it works

```
Antenna -> 1090 MHz filter -> RTL-SDR -> Raspberry Pi
                                          |-- readsb (writes /run/readsb/aircraft.json)
                                          |-- tar1090 (local map)
                                          |-- adsbexchange-feed
                                          '-- radar-bot (Telegram alerts)
```

## Files

| File | Purpose |
|---|---|
| `radar_bot.py` | Bot: reads `aircraft.json` and sends alerts |
| `aeronaves.example.json` | Example aircraft list (fictitious data) |
| `.env.example` | Credentials file template |
| `radar-bot.service` | systemd service |

## Quick bot install

```bash
mkdir -p ~/radar_bot && cd ~/radar_bot
# copy the files from this repository into this folder
cp aeronaves.example.json aeronaves.json   # edit with your own aircraft
cp .env.example .env && chmod 600 .env     # fill in TG_TOKEN and TG_CHAT_ID, set TG_LANG=en
python3 -m py_compile radar_bot.py && python3 -m json.tool aeronaves.json > /dev/null
sudo cp radar-bot.service /etc/systemd/system/   # adjust User and paths first
sudo systemctl daemon-reload && sudo systemctl enable --now radar-bot
```

The full steps (readsb, tar1090, ADS-B Exchange feed, creating the bot) are in the PDF.

## Message language

Set `TG_LANG` in `.env`: `pt` (default) or `en`. Use `TG_LANG=en` for English Telegram alerts. The bot's log lines are still in Portuguese.

## `aeronaves.json` format

```json
[
  {"nome": "DISPLAY NAME", "callsign": "PPXXX", "hex": ["AAAAAA", "BBBBBB"]}
]
```

`nome` is the display name. The bot reloads the file by itself every 5 minutes, no restart needed.

## Security

- The token and chat_id live only in `.env`, which `.gitignore` blocks.
- Never publish `.env` or your real aircraft list.
- If a token leaks, revoke it in @BotFather (`/mybots` -> API Token -> Revoke).
