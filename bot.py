import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

from utils import parse_mensagem, calcular_saldo, classificar_intervalo

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_DESTINO = 1454008370
ARQUIVO_DADOS = "dados_apostas.csv"

logging.basicConfig(level=logging.INFO)

if not os.path.exists(ARQUIVO_DADOS):
    df = pd.DataFrame(columns=["data", "hora", "esporte", "confronto", "estrategia", "linha", "odd", "resultado", "saldo", "intervalo"])
    df.to_csv(ARQUIVO_DADOS, index=False)

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

async def gerar_planilha():
    hoje = datetime.now().date()
    ontem = hoje - timedelta(days=1)

    df = pd.read_csv(ARQUIVO_DADOS)
    df_filtrado = df[df['data'] == ontem.strftime("%d/%m")]

    if not df_filtrado.empty:
        nome_arquivo = f"apostas_{ontem.strftime('%d-%m')}.xlsx"
        df_filtrado.to_excel(nome_arquivo, index=False)

        app = ApplicationBuilder().token(BOT_TOKEN).build()
        await app.bot.send_document(chat_id=CHAT_ID_DESTINO, document=open(nome_arquivo, 'rb'))
        os.remove(nome_arquivo)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensagem))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(gerar_planilha()), trigger='cron', hour=0, minute=0)
    scheduler.start()

    await app.run_polling()

import asyncio

if __name__ == '__main__':
    from telegram.ext import Application

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensagem))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: app.create_task(gerar_planilha()), trigger='cron', hour=0, minute=0)
    scheduler.start()

    # Executa polling de forma segura
    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        print("Bot encerrado.")
