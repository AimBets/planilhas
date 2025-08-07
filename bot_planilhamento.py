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
# Defina o fuso horário
TIMEZONE = pytz.timezone("America/Sao_Paulo")

def extrair_dados(mensagem):
    try:
        linhas = mensagem.split('\n')

        # Esporte: 🏀 se tiver (Q1)...(Q4), senão ⚽️
        if any(q in mensagem for q in ['(Q1)', '(Q2)', '(Q3)', '(Q4)']):
            esporte = '🏀'
        else:
            esporte = '⚽️'

        # Confronto: extrai só nomes dos jogadores
        confronto_linha = next((linha for linha in linhas if 'Confronto:' in linha), '')
        confronto = confronto_linha.split(':')[1].strip() if ':' in confronto_linha else ''
        confronto = confronto.replace('Confronto:', '').strip()

        # Estratégia
        estrategia_linha = next((linha for linha in linhas if '🏆' in linha), '')
        estrategia = estrategia_linha.split('🏆')[1].strip() if '🏆' in estrategia_linha else ''

        # Linha e odd
        linha_info = next((linha for linha in linhas if '@' in linha), '')
        linha = linha_info.split('@')[0].strip() if '@' in linha_info else ''
        odd = linha_info.split('@')[1].strip() if '@' in linha_info else ''

        # Resultado
        resultado = 'Green' if '✅' in mensagem else 'Red' if '🔴' in mensagem else ''
        saldo = "+100" if resultado == "Green" else "-100" if resultado == "Red" else "0"

        # Data e hora
        now = datetime.now(TIMEZONE)
        hora = now.strftime('%H:%M')
        data = now.strftime('%d/%m/%Y')

        # Intervalo
        hora_int = now.hour
        if 0 <= hora_int < 6:
            intervalo = 'MADRUGADA'
        elif 6 <= hora_int < 12:
            intervalo = 'MANHÃ'
        elif 12 <= hora_int < 18:
            intervalo = 'TARDE'
        else:
            intervalo = 'NOITE'

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
