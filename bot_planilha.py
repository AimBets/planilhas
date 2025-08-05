import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from apscheduler.schedulers.background import BackgroundScheduler

from utils import parse_mensagem, calcular_saldo, classificar_intervalo

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_DESTINO = 1454008370
ARQUIVO_DADOS = "dados_apostas.csv"

logging.basicConfig(level=logging.INFO)

# Estados da conversa
PEDIR_DATA = 1

# Garante existência do CSV
if not os.path.exists(ARQUIVO_DADOS):
    df = pd.DataFrame(columns=["data", "hora", "esporte", "confronto", "estrategia", "linha", "odd", "resultado", "saldo", "intervalo"])
    df.to_csv(ARQUIVO_DADOS, index=False)

# Trata mensagens comuns (apostas)
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.chat.id != CHAT_ID_DESTINO:
        return

    texto = update.message.text
    datahora = update.message.date.astimezone()

    dados = parse_mensagem(texto)
    if dados:
        saldo = calcular_saldo(dados['linha'], dados['resultado'])
        intervalo = classificar_intervalo(datahora.time())

        nova_linha = {
            "data": datahora.strftime("%d/%m"),
            "hora": datahora.strftime("%H:%M"),
            "esporte": dados['esporte'],
            "confronto": dados['confronto'],
            "estrategia": dados['estrategia'],
            "linha": dados['linha'],
            "odd": dados['linha'],
            "resultado": dados['resultado'],
            "saldo": saldo,
            "intervalo": intervalo
        }

        df = pd.read_csv(ARQUIVO_DADOS)
        df = pd.concat([df, pd.DataFrame([nova_linha])])
        df.to_csv(ARQUIVO_DADOS, index=False)

# Início do comando /gerarplanilha
async def iniciar_geracao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 Informe a data desejada (ex: 04/08/2025):")
    return PEDIR_DATA

# Recebe a data digitada e gera a planilha
async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_texto = update.message.text.strip()
    try:
        data_obj = datetime.strptime(data_texto, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("❌ Data inválida. Tente novamente no formato dd/mm/aaaa.")
        return PEDIR_DATA

    df = pd.read_csv(ARQUIVO_DADOS)
    df_filtrado = df[df['data'] == data_obj.strftime("%d/%m")]

    if df_filtrado.empty:
        await update.message.reply_text("⚠️ Nenhuma aposta encontrada para essa data.")
        return ConversationHandler.END

    nome_arquivo = f"apostas_{data_obj.strftime('%d-%m-%Y')}.xlsx"
    df_filtrado.to_excel(nome_arquivo, index=False)

    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(nome_arquivo, 'rb'))
    os.remove(nome_arquivo)
    return ConversationHandler.END

# Cancela caso o usuário desista
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Geração de planilha cancelada.")
    return ConversationHandler.END

# MAIN
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversa para gerar planilha
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerarplanilha", iniciar_geracao)],
        states={
            PEDIR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    # Handlers
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensagem))

    # Inicia o bot
    scheduler = BackgroundScheduler()
    scheduler.start()

    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        print("Bot encerrado.")
