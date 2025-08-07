import logging
import os
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import MessageHandler, filters (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import pandas as pd

# ========================
# CONFIGURAÇÕES
# ========================
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_USUARIO = 1454008370
CHAT_ID_CANAL = -1002780267394
FUSO = pytz.timezone("America/Sao_Paulo")

# ========================
# VARIÁVEL GLOBAL
# ========================
apostas_salvas = []

# ========================
# FUNÇÃO: EXTRAI DADOS
# ========================
def extrair_dados(mensagem: str, data: datetime) -> dict | None:
    try:
        esporte = "🏀 Basquete" if any(f"(Q{i})" in mensagem for i in range(1, 5)) else "⚽️ Futebol"
        confronto = mensagem.split("Confronto:")[1].split("\n")[0].strip()
        estrategia = mensagem.split("🏆")[1].split("@")[0].strip()
        linha = "@" + mensagem.split("@")[1].split("\n")[0].strip()
        odd = linha.split("@")[1]
        resultado = "GREEN" if "✅" in mensagem.upper() else "RED" if "❌" in mensagem.upper() else "?"
        saldo = f"+{float(odd) - 1:.2f}" if resultado == "GREEN" else "-1.00" if resultado == "RED" else "0.00"

        hora_str = mensagem.split("🕒")[1].split("\n")[0].strip()
        hora = datetime.strptime(hora_str, "%H:%M").time()

        hora_full = datetime.combine(data.date(), hora)
        hora_full = FUSO.localize(hora_full)

        if hora_full.hour < 12:
            intervalo = "MADRUGADA"
        elif hora_full.hour < 18:
            intervalo = "TARDE"
        else:
            intervalo = "NOITE"

        return {
            "DATA": data.strftime("%d/%m/%Y"),
            "HORA": hora.strftime("%H:%M"),
            "ESPORTE": esporte,
            "CONFRONTO": confronto,
            "ESTRATÉGIA": estrategia,
            "LINHA": linha,
            "ODD": odd,
            "RESULTADO": resultado,
            "SALDO": saldo,
            "INTERVALO": intervalo,
        }

    except Exception as e:
        print(f"Erro ao extrair dados: {e}")
        return None

# ========================
# HANDLER: NOVA MENSAGEM NO CANAL
# ========================
async def salvar_aposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat_id == CHAT_ID_CANAL:
        mensagem = update.channel_post.text
        data = update.channel_post.date.astimezone(FUSO)

        aposta = extrair_dados(mensagem, data)
        if aposta:
            apostas_salvas.append(aposta)

# ========================
# COMANDO: /gerar
# ========================
async def gerar_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID_USUARIO:
        return

    await update.message.reply_text("Informe a data desejada no formato DD/MM:")

    return 1  # Próximo estado da conversa

# ========================
# RESPOSTA: DATA PARA GERAÇÃO
# ========================
async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_str = update.message.text.strip()
    try:
        data_obj = datetime.strptime(data_str + "/2025", "%d/%m/%Y").date()
        dados_dia = [a for a in apostas_salvas if datetime.strptime(a['DATA'], "%d/%m/%Y").date() == data_obj]

        if not dados_dia:
            await update.message.reply_text("Nenhuma aposta encontrada para essa data.")
            return

        df = pd.DataFrame(dados_dia)
        nome_arquivo = f"planilha_{data_str.replace('/', '-')}.xlsx"
        caminho = f"/tmp/{nome_arquivo}"
        df.to_excel(caminho, index=False)

        await update.message.reply_document(document=open(caminho, "rb"))

    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")

# ========================
# GERA AS PLANILHAS DE 01/08 ATÉ A DATA ATUAL AO INICIAR
# ========================
async def gerar_planilhas_iniciais(app):
    hoje = datetime.now(FUSO).date()
    for dia in range(1, hoje.day + 1):
        data = datetime.strptime(f"{dia:02d}/08/2025", "%d/%m/%Y").date()
        dados_dia = [a for a in apostas_salvas if datetime.strptime(a['DATA'], "%d/%m/%Y").date() == data]
        if dados_dia:
            df = pd.DataFrame(dados_dia)
            nome_arquivo = f"/tmp/planilha_{data.strftime('%d-%m')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            print(f"✅ Planilha gerada: {nome_arquivo}")

# ========================
# MAIN
# ========================
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, salvar_aposta))
    app.add_handler(CommandHandler("gerar", gerar_planilha))
    app.add_handler(MessageHandler(filters.TEXT & filters.USER(user_id=CHAT_ID_USUARIO), receber_data))

    app.run_polling(allowed_updates=Update.ALL_TYPES, post_init=gerar_planilhas_iniciais)

if __name__ == "__main__":
    main()
