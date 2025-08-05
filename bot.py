import logging
import os
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from utils import parse_mensagem, calcular_saldo, classificar_intervalo

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_DESTINO = 1454008370
ARQUIVO_DADOS = "dados_apostas.csv"
PEDIR_DATA = 1

logging.basicConfig(level=logging.INFO)

if not os.path.exists(ARQUIVO_DADOS):
    df = pd.DataFrame(columns=["data", "hora", "esporte", "confronto", "estrategia", "linha", "odd", "resultado", "saldo", "intervalo"])
    df.to_csv(ARQUIVO_DADOS, index=False)

# ✅ Recebe mensagens de apostas normalmente
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

# ✅ Inicia o comando /gerarplanilha
async def gerarplanilha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message.chat.id != CHAT_ID_DESTINO:
        return
    await update.message.reply_text("🗓️ Informe a data desejada (ex: 04/08/2025):")
    return PEDIR_DATA

# ✅ Gera a planilha da data fornecida
async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_texto = update.message.text.strip()
    try:
        data = datetime.strptime(data_texto, "%d/%m/%Y").date()
    except:
        await update.message.reply_text("❌ Data inválida. Use o formato dd/mm/aaaa (ex: 04/08/2025).")
        return ConversationHandler.END

    try:
        df = pd.read_csv(ARQUIVO_DADOS)
        df_filtrado = df[df["data"] == data.strftime("%d/%m")]
        if df_filtrado.empty:
            await update.message.reply_text("⚠️ Nenhuma aposta encontrada para essa data.")
            return ConversationHandler.END

        nome_arquivo = f"apostas_{data.strftime('%d-%m')}.xlsx"
        df_filtrado.to_excel(nome_arquivo, index=False)

        await context.bot.send_document(chat_id=CHAT_ID_DESTINO, document=open(nome_arquivo, 'rb'))
        os.remove(nome_arquivo)
    except Exception as e:
        print("❌ [ERRO] Falha ao gerar planilha:", e)
        await update.message.reply_text("❌ Ocorreu um erro ao gerar a planilha.")
    return ConversationHandler.END

# ✅ Inicializa o bot com polling
if __name__ == '__main__':
    from telegram.ext import Application

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mensagem))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerarplanilha", gerarplanilha_cmd)],
        states={PEDIR_DATA: [MessageHandler(filters.TEXT & (~filters.COMMAND), receber_data)]},
        fallbacks=[]
    )

    app.add_handler(conv_handler)

    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        print("Bot encerrado.")
