import os
import pytz
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ChannelPostHandler
)
from openpyxl import Workbook

# ======================== CONFIG ========================
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CANAL_ID = -1002780267394
USUARIO_ID = 1454008370
FUSO_HORARIO = pytz.timezone("America/Sao_Paulo")
PASTA_PLANILHAS = "planilhas"
os.makedirs(PASTA_PLANILHAS, exist_ok=True)
# =======================================================

# Armazenamento em memória
mensagens_armazenadas = []

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def classificar_intervalo(hora_str):
    hora = int(hora_str.split(":")[0])
    if 0 <= hora < 6:
        return "MADRUGADA"
    elif 6 <= hora < 12:
        return "MANHÃ"
    elif 12 <= hora < 18:
        return "TARDE"
    else:
        return "NOITE"

def extrair_dados(msg: str, data_msg: datetime):
    esporte = "\U0001F3C0" if any(q in msg for q in ["(Q1)", "(Q2)", "(Q3)", "(Q4)"]) else "⚽"

    def buscar(termo, pos=1):
        try:
            return msg.split(termo)[pos].split("\n")[0].strip()
        except:
            return ""

    confronto = buscar("Confronto:")
    estrategia = buscar("🏆")
    linha = buscar("@")
    odd = buscar("@", 2).split()[0]
    resultado = "Green" if "✅" in msg else ("Red" if "🔴" in msg else "Pendente")
    saldo = buscar("Lucro:").replace("R$", "").replace(",", ".") if "Lucro:" in msg else ("+1" if resultado == "Green" else ("-1" if resultado == "Red" else "0"))

    data_str = data_msg.strftime("%d/%m")
    hora_str = data_msg.strftime("%H:%M")
    intervalo = classificar_intervalo(hora_str)

    return {
        "DATA": data_str,
        "HORA": hora_str,
        "ESPORTE": esporte,
        "CONFRONTO": confronto,
        "ESTRATÉGIA": estrategia,
        "LINHA": linha,
        "ODD": odd,
        "RESULTADO": resultado,
        "SALDO": saldo,
        "INTERVALO": intervalo,
    }

async def salvar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat_id == CANAL_ID:
        msg = update.channel_post.text
        data_msg = datetime.now(FUSO_HORARIO)
        dados = extrair_dados(msg, data_msg)
        mensagens_armazenadas.append(dados)
        logger.info(f"Mensagem salva: {dados}")

async def gerar_planilha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != USUARIO_ID:
        return

    await update.message.reply_text("Informe a data no formato DD/MM:")
    return 1

async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_input = update.message.text.strip()
    mensagens_filtradas = [m for m in mensagens_armazenadas if m["DATA"] == data_input]

    if not mensagens_filtradas:
        await update.message.reply_text("Nenhuma mensagem encontrada para essa data.")
        return ConversationHandler.END

    wb = Workbook()
    ws = wb.active
    ws.append(list(mensagens_filtradas[0].keys()))

    for linha in mensagens_filtradas:
        ws.append(list(linha.values()))

    nome_arquivo = f"{PASTA_PLANILHAS}/planilha_{data_input.replace('/', '-')}.xlsx"
    wb.save(nome_arquivo)

    await update.message.reply_document(open(nome_arquivo, "rb"))
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChannelPostHandler(salvar_mensagem))

    from telegram.ext import ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerar", gerar_planilha_handler)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)]},
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    logger.info("Bot rodando...")
    app.run_polling()

if __name__ == '__main__':
    main()
