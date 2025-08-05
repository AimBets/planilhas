import os
import re
import datetime
from collections import defaultdict
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from openpyxl import Workbook

# TOKEN do seu bot
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"

# Armazena apostas por data
apostas_por_data = defaultdict(list)

# Regex para extrair os dados da mensagem
padrao = re.compile(
    r"⚽️ (.+)\n🏆 (.+?) @([\d.]+)\n⚔ Confronto: (.+?)\n🔢 Placar: (.+?)\n🕒 Tempo: (.+?)\n\n(✅ Green|❌ Red|⚠️ Anulada)",
    re.DOTALL
)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bem-vindo! Use /gerarplanilha para gerar o relatório de apostas.")

# /GERARPLANILHA
async def gerarplanilha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 Informe a data desejada (ex: 04/08/2025):")
    return 1

# Receber data
async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_texto = update.message.text.strip()

    try:
        data_obj = datetime.datetime.strptime(data_texto, "%d/%m/%Y").date()
    except ValueError:
        await update.message.reply_text("❌ Data inválida. Use o formato dd/mm/aaaa.")
        return 1

    apostas = apostas_por_data.get(data_obj)
    if not apostas:
        await update.message.reply_text("⚠️ Nenhuma aposta encontrada para essa data.")
        return ConversationHandler.END

    # Criar planilha
    wb = Workbook()
    ws = wb.active
    ws.title = data_obj.strftime("%d-%m-%Y")
    ws.append(["ESPORTES", "MERCADO", "ODD", "CONFRONTO", "PLACAR", "TEMPO", "RESULTADO"])

    for aposta in apostas:
        ws.append(aposta)

    nome_arquivo = f"apostas_{data_obj.strftime('%d_%m_%Y')}.xlsx"
    wb.save(nome_arquivo)

    with open(nome_arquivo, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=nome_arquivo))

    os.remove(nome_arquivo)
    return ConversationHandler.END

# Captura mensagens do canal
async def capturar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.effective_message.text
    if not texto:
        return

    match = padrao.search(texto)
    if match:
        esporte, mercado, odd, confronto, placar, tempo, resultado = match.groups()
        data_aposta = datetime.date.today()
        apostas_por_data[data_aposta].append([
            esporte.strip(),
            mercado.strip(),
            odd.strip(),
            confronto.strip(),
            placar.strip(),
            tempo.strip(),
            resultado.strip()
        ])

# Cancelar comando
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Ação cancelada.")
    return ConversationHandler.END

# MAIN
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Conversa da planilha
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerarplanilha", gerarplanilha)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & filters.ALL, capturar))

    app.run_polling()

if __name__ == "__main__":
    main()
