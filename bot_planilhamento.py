import re
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

        # DATA e HORA da linha 'Atualizado em:'
        data_hora_match = next((linha for linha in linhas if 'Atualizado em:' in linha), None)
        if data_hora_match:
            dh = re.search(r'Atualizado em:\s*(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2})', data_hora_match)
            data = dh.group(1) if dh else ''
            hora = dh.group(2) if dh else ''
        else:
            data = ''
            hora = ''

        # ESPORTE: se achar (Q1), (Q2), (Q3) ou (Q4) na mensagem é basquete 🏀, senão ⚽
        if any(q in mensagem for q in ['(Q1)', '(Q2)', '(Q3)', '(Q4)']):
            esporte = '🏀'
        else:
            esporte = '⚽'

        # Função para extrair confronto só com nomes no formato "Nome vs Nome"
        def extrair_confronto(linha_completa):
            match = re.search(r'([A-Za-zÀ-ÿ\s]+ vs [A-Za-zÀ-ÿ\s]+)', linha_completa)
            if match:
                return match.group(1).strip()
            return ''

        # CONFRONTO
        confronto_match = next((linha for linha in linhas if linha.startswith('🏆')), '')
        confronto = extrair_confronto(confronto_match)

        # ESTRATÉGIA e LINHA
        estrategia = ''
        linha_valor = ''
        if confronto_match:
            estr_match = re.search(r'🏆\s*(.+?)\s*@', confronto_match)
            if estr_match:
                estrategia_linha = estr_match.group(1).strip()
                num_match = re.search(r'(\d+\.?\d*)', estrategia_linha)
                if num_match:
                    linha_valor = num_match.group(1)
                    estrategia = estrategia_linha.replace(linha_valor, '').strip()
                else:
                    estrategia = estrategia_linha

        # ODD
        odd_match = re.search(r'@(\d+\.?\d*)', confronto_match)
        odd = odd_match.group(1) if odd_match else ''

        # RESULTADO e SALDO
        resultado = ''
        saldo = ''
        for linha in linhas:
            if 'Status da Aposta:' in linha:
                if '✅' in linha or 'Green' in linha:
                    resultado = 'Green'
                elif '❌' in linha or 'Red' in linha:
                    resultado = 'Red'
            if 'Lucro:' in linha:
                lucro_match = re.search(r'(-?\d+\.?\d*)\s*Un', linha)
                if lucro_match:
                    saldo = lucro_match.group(0)

        # INTERVALO baseado na hora
        if hora:
            hora_int = int(hora.split(':')[0])
            if 0 <= hora_int < 4:
                intervalo = '00:00 às 03:59'
            elif 4 <= hora_int < 8:
                intervalo = '04:00 às 07:59'
            elif 8 <= hora_int < 12:
                intervalo = '08:00 às 11:59'
            elif 12 <= hora_int < 16:
                intervalo = '12:00 às 15:59'
            elif 16 <= hora_int < 20:
                intervalo = '16:00 às 19:59'
            else:
                intervalo = '20:00 às 23:59'
        else:
            intervalo = ''

        return {
            'DATA': data,
            'HORA': hora,
            'ESPORTE': esporte,
            'CONFRONTO': confronto,
            'ESTRATÉGIA': estrategia,
            'LINHA': linha_valor,
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
