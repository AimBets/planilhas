import re

def parse_mensagem(texto):
    try:
        esporte = "⚽️" if "Fifa" in texto else "🏀"
        estrategia_linha = re.search(r"🏆 (.*?) @(\d+(?:\.\d+)?)", texto)
        estrategia = estrategia_linha.group(1).rsplit(" ", 1)[0]
        linha = estrategia_linha.group(1).rsplit(" ", 1)[1]
        odd = estrategia_linha.group(2)
        confronto = re.search(r"⚔ Confronto: (.*?)\\n", texto).group(1)
        resultado = re.search(r"(✅ Green|❌ Red|🟩 Half_green|🟥 Half_red|⚠️ Anulada|⚪ Void)", texto).group(1)
        return {
            "esporte": esporte,
            "estrategia": estrategia,
            "linha": linha,
            "odd": odd,
            "confronto": confronto,
            "resultado": resultado
        }
    except:
        return None

def calcular_saldo(odd_str, resultado):
    try:
        odd = float(odd_str)
        if resultado == "✅ Green":
            return round(odd - 1, 2)
        elif resultado == "🟩 Half_green":
            return round((odd - 1) / 2, 2)
        elif resultado == "❌ Red":
            return -1
        elif resultado == "🟥 Half_red":
            return -0.5
        elif resultado in ["⚠️ Anulada", "⚪ Void"]:
            return 0
        else:
            return 0
    except:
        return 0

def classificar_intervalo(horario):
    h = horario.hour
    if 0 <= h < 4:
        return "00:00 às 03:59"
    elif 4 <= h < 8:
        return "04:00 às 07:59"
    elif 8 <= h < 12:
        return "08:00 às 11:59"
    elif 12 <= h < 16:
        return "12:00 às 15:59"
    elif 16 <= h < 20:
        return "16:00 às 19:59"
    else:
        return "20:00 às 23:59"
