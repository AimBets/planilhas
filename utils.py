import re

def parse_mensagem(texto):
    try:
        esporte = "Fifa" if "Fifa" in texto else "Outro"
        estrategia = re.search(r"🏆 (.*?) @", texto).group(1)
        linha = re.search(r"@(\d+\.\d+)", texto).group(1)
        odd = linha
        confronto = re.search(r"Confronto: (.*?)\n", texto).group(1)
        resultado = "Green" if "✅ Green" in texto else "Red" if "❌ Red" in texto else "Anulada"
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

def calcular_saldo(odd, resultado):
    try:
        odd = float(odd)
        if resultado.lower() == "green":
            return round(odd - 1, 2)
        elif resultado.lower() == "red":
            return -1.00
        else:
            return 0.00
    except:
        return 0.00

def classificar_intervalo(hora):
    if hora < hora.replace(hour=12):
        return "Manhã"
    elif hora < hora.replace(hour=18):
        return "Tarde"
    else:
        return "Noite"
