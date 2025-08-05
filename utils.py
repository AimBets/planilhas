import re
from datetime import time

def parse_mensagem(texto):
    try:
        esporte = "⚽️" if "⚽️" in texto else "🏀"
        estrategia_match = re.search(r'🏆 (.+?) @', texto)
        linha_match = re.search(r'@([\d.]+)', texto)
        confronto_match = re.search(r'⚔ Confronto: (.+)', texto)
        resultado_match = re.search(r'(✅ Green|🟩 Half_green|❌ Red|🟥 Half_red|⚪ Void|⚠️ Anulada)', texto)

        estrategia = estrategia_match.group(1).strip() if estrategia_match else ""
        linha = linha_match.group(1) if linha_match else ""
        confronto = confronto_match.group(1).strip() if confronto_match else ""
        resultado = resultado_match.group(1).strip() if resultado_match else ""

        return {
            "esporte": esporte,
            "estrategia": estrategia,
            "linha": linha,
            "confronto": confronto,
            "resultado": resultado
        }
    except Exception as e:
        print("Erro ao fazer parsing:", e)
        return None

def calcular_saldo(odd, resultado):
    try:
        odd = float(odd)
        if resultado == "✅ Green":
            return round(odd - 1, 2)
        elif resultado == "🟩 Half_green":
            return round((odd - 1) / 2, 2)
        elif resultado == "❌ Red":
            return -1
        elif resultado == "🟥 Half_red":
            return -0.5
        elif resultado in ["⚪ Void", "⚠️ Anulada"]:
            return 0
        return ""
    except:
        return ""

def classificar_intervalo(hora):
    hora_int = hora.hour
    base = (hora_int // 4) * 4
    inicio = time(base).strftime("%H:%M")
    fim = time(base + 3, 59).strftime("%H:%M")
    return f"{inicio} às {fim}"