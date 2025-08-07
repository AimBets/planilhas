import logging
import os
import pytz
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
import pandas as pd

# =================== CONFIGURAÇÕES ===================
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CANAL_ID = -1002780267394
USUARIO_ID = 1454008370
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# ========== ARMAZENAMENTO EM MEMÓRIA ==========
apostas = []

# ========== LOG ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== FUNÇÕES DE UTILIDADE ==========
def extrair_dados(mensagem):
    try:
        linhas = mensagem.split('\n')
        texto = mensagem  # para regex completo

        # ESPORTE: 🏀 se contém (Q1),(Q2),(Q3),(Q4), senão ⚽️
        esporte = '🏀' if any(q in mensagem for q in ['(Q1)', '(Q2)', '(Q3)', '(Q4)']) else '⚽️'

        import re

        # CONFRONTO: pega só os nomes entre @ e - 🔢
        confronto_match = re.search(r'@[\d.]+\s*-\s*(.*?)\s*-\s*🔢', texto)
        confronto = confronto_match.group(1).strip() if confronto_match else ''

        # ESTRATÉGIA: texto após 🏆 até antes do @
        estrategia_match = re.search(r'🏆\s*(.*?)\s*@', texto)
        estrategia = estrategia_match.group(1).strip() if estrategia_match else ''

        # LINHA: número antes do @ (ex: 2.75)
        linha_match = re.search(r'🏆\s*.*?(\d+\.?\d*)\s*@', texto)
        linha = linha_match.group(1) if linha_match else ''

        # ODD: número após @
        odd_match = re.search(r'@(\d+\.?\d*)', texto)
        odd = odd_match.group(1) if odd_match else ''

        # RESULTADO: Status da Aposta (ex: Green, Red, Half_green)
        resultado_match = re.search(r'Status da Aposta:\s*([^\n]+)', texto)
        resultado = resultado_match.group(1).strip() if resultado_match else ''

        # SALDO: pega valor após "Lucro: "
        saldo_match = re.search(r'Lucro:\s*([-\d.,]+)', texto)
        saldo = saldo_match.group(1).replace(',', '.') if saldo_match else ''

        # DATA e HORA da linha "Atualizado em:"
        atualizado_match = re.search(r'Atualizado em:\s*(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2})', texto)
        if atualizado_match:
            data = atualizado_match.group(1)
            hora = atualizado_match.group(2)
        else:
            now = datetime.now(TIMEZONE)
            data = now.strftime('%d/%m/%Y')
            hora = now.strftime('%H:%M')

        # INTERVALO: baseado na hora, formato exato solicitado
        h = int(hora.split(':')[0])
        if 0 <= h <= 3:
            intervalo = '00:00 às 03:59'
        elif 4 <= h <= 7:
            intervalo = '04:00 às 07:59'
        elif 8 <= h <= 11:
            intervalo = '08:00 às 11:59'
        elif 12 <= h <= 15:
            intervalo = '12:00 às 15:59'
        elif 16 <= h <= 19:
            intervalo = '16:00 às 19:59'
        else:
            intervalo = '20:00 às 23:59'

        return {
            'DATA': data,
            'HORA': hora,
            'ESPORTE': esporte,
            'CONFRONTO': confronto,
            'ESTRATÉGIA': estrategia,
            'LINHA': linha,
            'ODD': odd,
            'RESULTADO': resultado,
            'SALDO': saldo,
            'INTERVALO': intervalo
        }
    except Exception as e:
        logging.error(f"Erro ao extrair dados: {e}")
        return None

# ========== HANDLER DE MENSAGENS DO CANAL ==========
async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post:
        mensagem = update.channel_post.text
        dados = extrair_dados(mensagem)
        if dados:
            apostas.append(dados)
            logging.info(f"Aposta registrada: {dados}")

# ========== COMANDO /gerar ==========
GERAR_DATA = 1

async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Informe a data desejada no formato DD/MM:")
    return GERAR_DATA

async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_input = update.message.text.strip()
    filtradas = [a for a in apostas if a['DATA'] == data_input]

    if not filtradas:
        await update.message.reply_text(f"Nenhuma aposta encontrada para {data_input}.")
        return ConversationHandler.END

    df = pd.DataFrame(filtradas)
    nome_arquivo = f"apostas_{data_input.replace('/', '-')}.xlsx"
    df.to_excel(nome_arquivo, index=False)

    await update.message.reply_document(document=open(nome_arquivo, 'rb'))
    os.remove(nome_arquivo)
    return ConversationHandler.END

# ========== GERAÇÃO RETROATIVA ==========
async def gerar_planilhas_iniciais(app):
    dias = [f"{str(d).zfill(2)}/08/2025" for d in range(1, 8)]
    for data in dias:
        filtradas = [a for a in apostas if a['DATA'] == data]
        if filtradas:
            df = pd.DataFrame(filtradas)
            nome_arquivo = f"apostas_{data.replace('/', '-')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            logging.info(f"Planilha gerada retroativamente: {nome_arquivo}")

# ========== FUNÇÃO MAIN ==========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    canal_handler = MessageHandler(filters.ALL & filters.Chat(CANAL_ID), receber_mensagem)
    app.add_handler(canal_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gerar", gerar)],
        states={GERAR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)]},
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    async def post_init(app):
        await gerar_planilhas_iniciais(app)

    # ✅ Aqui está a correção
    app.post_init = post_init

    app.run_polling()

if __name__ == '__main__':
    main()
