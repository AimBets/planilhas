import logging
import os
import csv
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler
import re
import pytz

# ============ CONFIGURAÇÕES ============
TOKEN = "8399571746:AAFXxkkJOfOP8cWozYKUnitQTDPTmLpWky8"
CANAL_ID = -1002780267394
CAMINHO_BASE = "planilha_base.csv"

# ============ LOG ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ INTERVALO DE HORAS ============
def intervalo_por_hora(hora: str):
    h = int(hora.split(":")[0])
    inicio = (h // 4) * 4
    fim = inicio + 3
    return f"{str(inicio).zfill(2)}:00 às {str(fim).zfill(2)}:59"

# ============ EXTRAÇÃO DE DADOS ============
def extrair_dados(texto):
    try:
        if "Status da Aposta:" not in texto or "Atualizado em:" not in texto:
            return None

        status_match = re.search(r"Status da Aposta: (✅ Green|❌ Red|🟡 Anulada)", texto)
        lucro_match = re.search(r"Lucro: ([\d.,\-]+)", texto)
        atualizado_match = re.search(r"Atualizado em: (\d{2}/\d{2}/\d{4} \d{2}:\d{2})", texto)
        evento_match = re.search(r"🏆 (.+?) @([\d.]+) - (.+?) -", texto)
        tempo_match = re.search(r"🕒 ([\d:]+(?: \(Q[1-4]\))?)", texto)

        if not all([status_match, lucro_match, atualizado_match, evento_match, tempo_match]):
            logger.warning(f"Mensagem ignorada, dados incompletos:\n{texto}")
            return None

        status = status_match.group(1)
        lucro = float(lucro_match.group(1).replace(",", "."))
        atualizado = atualizado_match.group(1)

        estrategia_linha = evento_match.group(1).rsplit(" ", 1)
        estrategia = estrategia_linha[0]
        linha = estrategia_linha[1]
        odd = evento_match.group(2)
        confronto = evento_match.group(3)

        tempo_str = tempo_match.group(1)
        esporte = "🏀" if any(q in tempo_str for q in ["Q1", "Q2", "Q3", "Q4"]) else "⚽️"

        dt_obj = datetime.strptime(atualizado, "%d/%m/%Y %H:%M")
        data = dt_obj.strftime("%d/%m/%Y")
        hora = dt_obj.strftime("%H:%M")
        intervalo = intervalo_por_hora(hora)

        return {
            "DATA": data,
            "HORA": hora,
            "ESPORTE": esporte,
            "CONFRONTO": confronto,
            "ESTRATÉGIA": estrategia,
            "LINHA": linha,
            "ODD": odd,
            "RESULTADO": status,
            "SALDO": lucro,
            "INTERVALO": intervalo
        }
    except Exception as e:
        logger.error(f"Erro ao extrair dados: {e}\nMensagem:\n{texto}")
        return None


# ============ SALVAR NA BASE ============
def salvar_dados(dados):
    existe = os.path.exists(CAMINHO_BASE)
    with open(CAMINHO_BASE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dados.keys())
        if not existe:
            writer.writeheader()
        writer.writerow(dados)

# ============ ESCUTAR MENSAGENS ============
async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CANAL_ID:
        texto = update.channel_post.text
        dados = extrair_dados(texto)
        if dados:
            salvar_dados(dados)

# ============ COMANDO /GERAR ============
GERAR_DATA = range(1)

async def gerar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Informe a data desejada no formato DD/MM/AAAA:")
    return GERAR_DATA

async def receber_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_desejada = update.message.text.strip()
    try:
        datetime.strptime(data_desejada, "%d/%m/%Y")
        nome_arquivo = data_desejada.replace("/", "-") + ".csv"
        linhas_filtradas = []

        with open(CAMINHO_BASE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["DATA"] == data_desejada:
                    linhas_filtradas.append(row)

        if linhas_filtradas:
            with open(nome_arquivo, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=linhas_filtradas[0].keys())
                writer.writeheader()
                writer.writerows(linhas_filtradas)

            await update.message.reply_document(open(nome_arquivo, "rb"))
            os.remove(nome_arquivo)
        else:
            await update.message.reply_text("Nenhuma aposta encontrada para essa data.")
    except:
        await update.message.reply_text("Data inválida. Tente novamente no formato DD/MM/AAAA.")
    return ConversationHandler.END

# ============ INICIAR BOT ============
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, processar_mensagem))

    conv = ConversationHandler(
        entry_points=[CommandHandler("gerar", gerar)],
        states={GERAR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data)]},
        fallbacks=[],
    )
    app.add_handler(conv)

    logger.info("Bot iniciado.")
    app.run_polling()

if __name__ == "__main__":
    main()
