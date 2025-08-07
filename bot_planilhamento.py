import os
import pytz
import datetime
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)
import pandas as pd

# Dados fixos
CANAL_ID = -1002780267394
ADMIN_ID = 1454008370
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# Armazenamento das mensagens recebidas
mensagens_apostas = []

# Função para determinar o intervalo com base na hora
def definir_intervalo(hora):
    if 0 <= hora < 6:
        return "MADRUGADA"
    elif 6 <= hora < 12:
        return "MANHÃ"
    elif 12 <= hora < 18:
        return "TARDE"
    else:
        return "NOITE"

# Função para calcular o saldo com base no resultado
def calcular_saldo(resultado):
    if "green" in resultado.lower():
        return 100
    elif "red" in resultado.lower():
        return -100
    else:
        return 0

# Identificação do esporte
def identificar_esporte(msg):
    return "🏀" if any(q in msg for q in ["(Q1)", "(Q2)", "(Q3)", "(Q4)"]) else "⚽️"

# Extração dos dados da mensagem
def extrair_dados(msg, data_msg, hora_msg):
    esporte = identificar_esporte(msg)
    confronto = msg.split("Confronto:")[1].split("\n")[0].strip() if "Confronto:" in msg else ""
    estrategia = msg.split("🏆")[-1].split("@")[0].strip() if "🏆" in msg else ""
    linha = msg.split("@")[-1].split("\n")[0].strip() if "@" in msg else ""
    odd = linha.split(" ")[0] if linha else ""
    resultado = "Green" if "✅" in msg else "Red" if "❌" in msg else "Pendente"
    saldo = calcular_saldo(resultado)
    intervalo = definir_intervalo(hora_msg.hour)

    return {\        "DATA": data_msg.strftime("%d/%m"),
        "HORA": hora_msg.strftime("%H:%M"),
        "ESPORTE": esporte,
        "CONFRONTO": confronto,
        "ESTRATÉGIA": estrategia,
        "LINHA": linha,
        "ODD": odd,
        "RESULTADO": resultado,
        "SALDO": saldo,
        "INTERVALO": intervalo
    }

# Manipulador de mensagens recebidas do canal
async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CANAL_ID:
        msg = update.channel_post.text
        data_hora = datetime.datetime.now(TIMEZONE)
        dados = extrair_dados(msg, data_hora.date(), data_hora)
        mensagens_apostas.append(dados)

# Geração da planilha por data
async def gerar_planilha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text("Digite a data desejada no formato DD/MM:")
    context.user_data['esperando_data'] = True

# Tratamento da data informada após /gerar
async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('esperando_data'):
        data_digitada = update.message.text.strip()
        df = pd.DataFrame([m for m in mensagens_apostas if m['DATA'] == data_digitada])

        if df.empty:
            await update.message.reply_text("Nenhuma aposta encontrada para esta data.")
        else:
            nome_arquivo = f"planilha_{data_digitada.replace('/', '-')}.xlsx"
            caminho = os.path.join("/mnt/data", nome_arquivo)
            df.to_excel(caminho, index=False)
            await update.message.reply_document(document=open(caminho, "rb"))

        context.user_data['esperando_data'] = False

# Geração automática de planilhas retroativas ao iniciar o bot
async def gerar_planilhas_iniciais(app):
    datas = [(datetime.date(2025, 8, dia)).strftime("%d/%m") for dia in range(1, 8)]
    for data in datas:
        df = pd.DataFrame([m for m in mensagens_apostas if m['DATA'] == data])
        if not df.empty:
            nome_arquivo = f"planilha_{data.replace('/', '-')}.xlsx"
            caminho = os.path.join("/mnt/data", nome_arquivo)
            df.to_excel(caminho, index=False)

# Inicialização
def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, receber_mensagem))
    app.add_handler(CommandHandler("gerar", gerar_planilha_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), receber_data))

    app.run_polling(allowed_updates=Update.ALL_TYPES, post_init=gerar_planilhas_iniciais)

if __name__ == '__main__':
    main()
