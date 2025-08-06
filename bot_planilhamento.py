import telegram
print("📦 Versão do python-telegram-bot:", telegram.__version__)
import logging
import os
import pandas as pd
from datetime import datetime, time
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler, ChannelPostHandler
import re

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CHAT_ID_USUARIO = 1454008370
ARQUIVO_DADOS = "dados_apostas.csv"

AGUARDANDO_DATA = 1

logging.basicConfig(level=logging.INFO)

if not os.path.exists(ARQUIVO_DADOS):
    colunas = ["data", "hora", "esporte", "confronto", "estrategia", "linha", "odd", "resultado", "saldo", "intervalo"]
    pd.DataFrame(columns=colunas).to_csv(ARQUIVO_DADOS, index=False)

def classificar_intervalo(hora):
    if time(0, 0) <= hora < time(4, 0):
        return "00:00 às 03:59"
    elif time(4, 0) <= hora < time(8, 0):
        return "04:00 às 07:59"
    elif time(8, 0) <= hora < time(12, 0):
        return "08:00 às 11:59"
    elif time(12, 0) <= hora < time(16, 0):
        return "12:00 às 15:59"
    elif time(16, 0) <= hora < time(20, 0):
        return "16:00 às 19:59"
    elif time(20, 0) <= hora < time(23, 59, 59):
        return "20:00 às 23:59"
    else:
        return "00:00 às 03:59"

def parse_mensagem(texto):
    try:
        estrategia_match = re.search(r"🎯 Aposta: (.*?)\s[\d.]+\s?\(\)", texto)
        linha_odd_match = re.search(r"🏆 (.*?)@(\d+\.\d+)", texto)
        confronto_match = re.search(r"- (.*?) -", texto)
        resultado_match = re.search(r"Status da Aposta: (.*?)\n", texto)
        saldo_match = re.search(r"Lucro: ([\-\d.]+) Un", texto)
        atualizado_em = re.search(r"Atualizado em: (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})", texto)
        tempo_match = re.search(r"🕒 .*?(\(Q\d\))?", texto)

        if not (estrategia_match and linha_odd_match and confronto_match and resultado_match and saldo_match and atualizado_em):
            return None

        estrategia = estrategia_match.group(1).strip()
        linha = linha_odd_match.group(1).split(estrategia)[-1].strip()
        odd = linha_odd_match.group(2)
        confronto = confronto_match.group(1).strip()
        resultado = resultado_match.group(1).strip()
        saldo = saldo_match.group(1).strip()
        data = atualizado_em.group(1)
        hora = atualizado_em.group(2)
        qx = tempo_match.group(1)

        esporte = "🏀" if qx else "⚽️"

        horario = datetime.strptime(hora, "%H:%M").time()
        intervalo = classificar_intervalo(horario)

        return {
            "data": datetime.strptime(data, "%d/%m/%Y").strftime("%d/%m"),
            "hora": hora,
            "esporte": esporte,
            "confronto": confronto,
            "estrategia": estrategia,
            "linha": linha,
            "odd": odd,
            "resultado": resultado,
            "saldo": saldo,
            "intervalo": intervalo
        }
    except:
        return None

async def salvar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.channel_post.text if update.channel_post else None
    if not texto:
        return
    dados = parse_mensagem(texto)
    if dados:
        df = pd.read_csv(ARQUIVO_DADOS)
        df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
        df.to_csv(ARQUIVO_DADOS, index=False)
        logging.info(f"Aposta registrada: {dados}")

async def comando_gerar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CHAT_ID_USUARIO:
        return
    await update.message.reply_text("📅 Informe a data desejada (formato DD/MM):")
    return AGUARDANDO_DATA

async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.message.text.strip()
    try:
        datetime.strptime(data, "%d/%m")
        df = pd.read_csv(ARQUIVO_DADOS)
        df_filtrado = df[df['data'] == data]
        if df_filtrado.empty:
            await update.message.reply_text("⚠️ Nenhuma aposta encontrada nessa data.")
        else:
            nome_arquivo = f"apostas_{data.replace('/', '-')}.xlsx"
            df_filtrado.to_excel(nome_arquivo, index=False)
            await update.message.reply_document(document=open(nome_arquivo, "rb"))
            os.remove(nome_arquivo)
    except ValueError:
        await update.message.reply_text("❌ Data inválida. Use o formato DD/MM.")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Comando cancelado.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerar", comando_gerar)],
        states={AGUARDANDO_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)]},
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, salvar_mensagem))

    app.run_polling()

