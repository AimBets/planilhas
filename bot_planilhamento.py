
import json
import os
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ChatAction
import pytz
import pandas as pd
import re

BOT_TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CANAL_ID = -1002780267394
CHAT_ID_USUARIO = 1454008370
DATA_SOLICITADA = range(1)
ARQUIVO_DADOS = "dados_salvos.json"

# Garantir pasta de planilhas
os.makedirs("planilhas", exist_ok=True)

# Carrega mensagens antigas (se existir)
if os.path.exists(ARQUIVO_DADOS):
    with open(ARQUIVO_DADOS, "r") as f:
        mensagens_salvas = json.load(f)
else:
    mensagens_salvas = []

def extrair_intervalo(hora: str):
    h = int(hora.split(":")[0])
    blocos = [(0, 3), (4, 7), (8, 11), (12, 15), (16, 19), (20, 23)]
    for inicio, fim in blocos:
        if inicio <= h <= fim:
            return f"{str(inicio).zfill(2)}:00 às {str(fim).zfill(2)}:59"

def extrair_dados(mensagem: str):
    try:
        atualizado = re.search(r"Atualizado em: (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})", mensagem)
        data = atualizado.group(1)
        hora = atualizado.group(2)
        esporte = "🏀" if any(q in mensagem for q in ["(Q1)", "(Q2)", "(Q3)", "(Q4)"]) else "⚽️"
        confronto_match = re.search(r"🏆 .*? - (.*?) - 🔢", mensagem)
        confronto = confronto_match.group(1).strip() if confronto_match else "?"
        mercado = re.search(r"🎲 Mercado: (.*?)\n", mensagem).group(1).strip()
        linha_match = re.search(r"🏆 (.*?)@", mensagem)
        linha = linha_match.group(1).strip() if linha_match else mercado
        odd_match = re.search(r"@([0-9.]+)", mensagem)
        odd = float(odd_match.group(1)) if odd_match else 0
        resultado_match = re.search(r"Status da Aposta: (.*?)\n", mensagem)
        resultado = resultado_match.group(1).strip() if resultado_match else "?"
        saldo_match = re.search(r"Lucro: ([\d\.\-]+) Un", mensagem)
        saldo = float(saldo_match.group(1)) if saldo_match else 0
        intervalo = extrair_intervalo(hora)

        return {
            "DATA": data,
            "HORA": hora,
            "ESPORTE": esporte,
            "CONFRONTO": confronto,
            "ESTRATÉGIA": mercado,
            "LINHA": linha,
            "ODD": odd,
            "RESULTADO": resultado,
            "SALDO": saldo,
            "INTERVALO": intervalo
        }

    except Exception as e:
        print("Erro ao extrair dados:", e)
        return None

async def salvar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CANAL_ID:
        texto = update.channel_post.text
        if "Status da Aposta:" in texto:
            mensagens_salvas.append(texto)
            with open(ARQUIVO_DADOS, "w") as f:
                json.dump(mensagens_salvas, f)

async def gerar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Qual data deseja gerar a planilha? (formato DD/MM)")
    return DATA_SOLICITADA

async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_texto = update.message.text.strip()
    if not re.match(r"\d{2}/\d{2}", data_texto):
        await update.message.reply_text("Formato inválido. Envie no formato DD/MM.")
        return ConversationHandler.END

    data_filtro = f"{data_texto}/2025"
    dados_filtrados = []

    for msg in mensagens_salvas:
        if data_filtro in msg:
            dados = extrair_dados(msg)
            if dados:
                dados_filtrados.append(dados)

    if not dados_filtrados:
        await update.message.reply_text("Nenhuma aposta encontrada nessa data.")
        return ConversationHandler.END

    df = pd.DataFrame(dados_filtrados)
    nome_arquivo = f"planilhas/Planilha_{data_texto.replace('/', '-')}.xlsx"
    df.to_excel(nome_arquivo, index=False)

    await update.message.reply_text("Planilha gerada com sucesso!")
    await context.bot.send_document(chat_id=CHAT_ID_USUARIO, document=InputFile(nome_arquivo))
    return ConversationHandler.END

async def gerar_planilhas_iniciais(app):
    datas = ["01/08", "02/08", "03/08", "04/08", "05/08"]
    for d in datas:
        data_filtro = f"{d}/2025"
        dados_filtrados = []
        for msg in mensagens_salvas:
            if data_filtro in msg:
                dados = extrair_dados(msg)
                if dados:
                    dados_filtrados.append(dados)
        if dados_filtrados:
            df = pd.DataFrame(dados_filtrados)
            nome_arquivo = f"planilhas/Planilha_{d.replace('/', '-')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            await app.bot.send_document(chat_id=CHAT_ID_USUARIO, document=InputFile(nome_arquivo))

def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("gerar", gerar_command)],
        states={DATA_SOLICITADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)]},
        fallbacks=[]
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.ALL, salvar_mensagem))

    import asyncio
    async def iniciar_e_rodar():
        await gerar_planilhas_iniciais(app)
        await app.run_polling(allowed_updates=Update.ALL_TYPES)

    asyncio.run(iniciar_e_rodar())


if __name__ == "__main__":
    main()
