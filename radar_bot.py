import requests
import time
import json
import socket
import os
import logging
from pathlib import Path

# --- CONFIGURAÇÕES GERAIS ---
BASE_DIR = Path(__file__).resolve().parent
AIRCRAFT_JSON = "/run/readsb/aircraft.json"
AERONAVES_JSON = BASE_DIR / "aeronaves.json"
ENV_FILE = BASE_DIR / ".env"

INTERVALO_LOOP = 10          # segundos entre leituras do aircraft.json
INTERVALO_RECARGA_DB = 300   # segundos entre recarregar aeronaves.json (5 min)
JANELA_ANTISPAM = 1800       # 30 minutos sem repetir alerta da mesma aeronave

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("radar_bot")


# --- CARREGAR VARIÁVEIS DE AMBIENTE (.env simples, sem depender de lib externa) ---
def carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return
    with open(caminho, "r") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip())


carregar_env(ENV_FILE)

TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

if not TOKEN or not CHAT_ID:
    log.error(
        "TG_TOKEN e/ou TG_CHAT_ID não configurados. "
        "Copie .env.example para .env e preencha os valores."
    )
    raise SystemExit(1)


# --- BANCO DE AERONAVES (externo, recarregável sem reiniciar o bot) ---
def carregar_banco_aeronaves(caminho: Path) -> dict:
    """
    Lê aeronaves.json (lista de {nome, callsign, hex}) e monta um dicionário
    único de busca por callsign OU hex, ambos em maiúsculas.
    O campo "hex" aceita tanto uma string única quanto uma lista de códigos
    (útil quando a mesma aeronave tem mais de um hex registrado/histórico).
    """
    banco = {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            lista = json.load(f)
        for item in lista:
            nome = item.get("nome", "").strip()
            callsign = item.get("callsign", "").strip().upper()
            hex_valor = item.get("hex", [])

            if isinstance(hex_valor, str):
                hex_lista = [hex_valor] if hex_valor.strip() else []
            elif isinstance(hex_valor, list):
                hex_lista = hex_valor
            else:
                hex_lista = []

            if not nome:
                continue
            if callsign:
                banco[callsign] = nome
            for h in hex_lista:
                h = h.strip().upper()
                if h:
                    banco[h] = nome
        log.info(f"Banco de aeronaves carregado: {len(lista)} aeronaves cadastradas.")
    except FileNotFoundError:
        log.error(f"Arquivo {caminho} não encontrado.")
    except json.JSONDecodeError as e:
        log.error(f"Erro ao ler {caminho} (JSON inválido): {e}")
    return banco


def enviar_telegram(mensagem: str, tentativas: int = 3) -> bool:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.post(url, data=payload, timeout=10)
            if r.status_code == 200:
                return True
            log.warning(f"Telegram respondeu {r.status_code}: {r.text[:200]}")
        except requests.exceptions.RequestException as e:
            log.warning(f"Tentativa {tentativa}/{tentativas} falhou: {e}")
        if tentativa < tentativas:
            time.sleep(2)
    log.error("Falha ao enviar mensagem ao Telegram após todas as tentativas.")
    return False


def get_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def montar_mensagem(nome_exibir: str, callsign: str, hex_id: str, ac: dict, meu_ip: str) -> str:
    alt = ac.get("alt_baro", "N/A")
    velocidade = ac.get("gs", "N/A")       # ground speed, em nós
    rumo = ac.get("track", "N/A")          # direção em graus
    squawk = ac.get("squawk", "N/A")

    return (
        f"📡 *Alvo Identificado!*\n"
        f"✈️ *Identificação:* `{nome_exibir}`\n"
        f"🆔 *Callsign:* `{callsign if callsign else 'N/A'}`\n"
        f"📟 *Hex (ICAO):* `{hex_id}`\n"
        f"📏 *Altitude:* {alt} ft\n"
        f"🚀 *Velocidade:* {velocidade} kt\n"
        f"🧭 *Rumo:* {rumo}°\n"
        f"📻 *Squawk:* `{squawk}`\n\n"
        f"[Abrir Mapa Local](http://{meu_ip}/tar1090)"
    )


def limpar_avisados(avisados: dict, agora: float) -> dict:
    return {k: v for k, v in avisados.items() if agora - v < JANELA_ANTISPAM}


def main():
    avisados = {}
    meu_ip = get_ip()
    banco_aeronaves = carregar_banco_aeronaves(AERONAVES_JSON)
    ultima_recarga_db = time.time()
    ultima_limpeza = time.time()

    log.info(f"Bot iniciado (Filtro Exclusivo) no IP: {meu_ip}")
    time.sleep(2)

    enviar_telegram(
        f"🚀 *Radar ADS-B Online!*\n📍 *IP:* `{meu_ip}`\n"
        f"Monitorando {len(banco_aeronaves)} identificadores cadastrados."
    )

    while True:
        agora = time.time()

        # Recarrega o banco de aeronaves periodicamente, sem reiniciar o bot
        if agora - ultima_recarga_db > INTERVALO_RECARGA_DB:
            banco_aeronaves = carregar_banco_aeronaves(AERONAVES_JSON)
            ultima_recarga_db = agora

        # Limpa entradas antigas do dicionário de antispam
        if agora - ultima_limpeza > 3600:
            avisados = limpar_avisados(avisados, agora)
            ultima_limpeza = agora
            log.info(f"Limpeza de 'avisados' concluída. {len(avisados)} entradas ativas.")

        try:
            if not os.path.exists(AIRCRAFT_JSON):
                log.warning(f"Aguardando {AIRCRAFT_JSON}...")
                time.sleep(INTERVALO_LOOP)
                continue

            with open(AIRCRAFT_JSON, "r") as f:
                dados = json.load(f)

            for ac in dados.get("aircraft", []):
                callsign = ac.get("flight", "").strip().upper()
                hex_id = ac.get("hex", "").upper()

                if not hex_id:
                    continue

                nome_exibir = banco_aeronaves.get(callsign) or banco_aeronaves.get(hex_id)
                if not nome_exibir:
                    continue

                if hex_id not in avisados or (agora - avisados[hex_id] > JANELA_ANTISPAM):
                    msg = montar_mensagem(nome_exibir, callsign, hex_id, ac, meu_ip)
                    if enviar_telegram(msg):
                        avisados[hex_id] = agora

        except json.JSONDecodeError:
            # O readsb pode estar no meio de uma escrita do arquivo; ignora e tenta de novo no próximo ciclo
            log.debug("aircraft.json incompleto/corrompido nesta leitura, ignorando ciclo.")
        except Exception as e:
            log.error(f"Erro inesperado no loop: {e}")

        time.sleep(INTERVALO_LOOP)


if __name__ == "__main__":
    main()
