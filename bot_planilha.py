import logging
import os
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    ContextTypes, ConversationHandler, filters
)
from utils import parse_mensagem, calcular_saldo, classificar_intervalo

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_ADMIN = 1454008370
ARQUIVO_DADOS = "dados_apostas.csv"

logging.basicConfig(level=logging.INFO)

# Criar CSV se não existir
if not os.path.exists(ARQUIVO_DADOS):
    df = pd.DataFrame(columns=[
        "data", "hora", "esporte", "confronto", "estrategia",
        "linha", "odd", "resultado", "saldo", "intervalo"
    ])
    df.to_csv(ARQUIVO_DADOS, index=False)

# Armazenar apostas recebidas no canal
async def salvar_aposta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    texto = message.text
    datahora = message.date.astimezone()

    dados = parse_mensagem(texto)
    if dados:
        saldo = calcular_saldo(dados['linha'], dados['resultado'])
        intervalo = classificar_intervalo(datahora.time())

        nova_linha = {
            "data": datahora.strftime("%d/%m/%Y"),
            "hora": datahora.strftime("%H:%M"),
            "esporte": dados['esporte'],
            "confronto": dados['confronto'],
            "estrategia": dados['estrategia'],
            "linha": dados['linha'],
            "odd": dados['odd'],
            "resultado": dados['resultado'],
            "saldo": saldo,
            "intervalo": intervalo
        }

        df = pd.read_csv(ARQUIVO_DADOS)
        df = pd.concat([df, pd.DataFrame([nova_linha])])
        df.to_csv(ARQUIVO_DADOS, index=False)
        logging.info(f"Aposta salva: {nova_linha}")

# Etapa da conversa: receber data
ASKING_DATA = 1

async def gerar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Digite a data que deseja gerar a planilha (formato: dd/mm/aaaa):")
    return ASKING_DATA

# Etapa da conversa: gerar planilha
async def gerar_planilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        data = datetime.strptime(texto, "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("Data inválida. Use o formato: dd/mm/aaaa")
        return ConversationHandler.END

    df = pd.read_csv(ARQUIVO_DADOS)
    df_filtrado = df[df['data'] == data]

    if df_filtrado.empty:
        await update.message.reply_text("Nenhuma aposta encontrada para essa data.")
    else:
        nome_arquivo = f"apostas_{data.replace('/', '-')}.xlsx"
        df_filtrado.to_excel(nome_arquivo, index=False)
        await update.message.reply_document(document=open(nome_arquivo, 'rb'))
        os.remove(nome_arquivo)

    return ConversationHandler.END

# Cancelamento da conversa
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

# Início do bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.CHANNEL, salvar_aposta))

    conversa_handler = ConversationHandler(
        entry_points=[CommandHandler("gerarplanilha", gerar_command)],
        states={ASKING_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, gerar_planilha)]},
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(conversa_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
