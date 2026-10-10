from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
import os, chess, chess.engine, urllib.request, json, re

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGroq(
    temperature=0,
    model_name="openai/gpt-oss-20b",
    groq_api_key=os.environ.get("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") # LEMBRE-SE DE USAR SUA NOVA CHAVE NO RENDER!
)

search = DuckDuckGoSearchRun()

# BANCO DE RÁDIOS BRASILEIRAS
RADIOS_BRASIL = {
    "jovem pan": "https://stream.zeno.fm/yn65fsaurfhvv",
    "jovem pan news": "https://stream.zeno.fm/0p2s4v5a7g8uv",
    "cbn": "https://n008a-eu.rcs.revma.com/ypqt40u0x1zuv",
    "antena 1": "https://antena1.stream.com.br/antena1",
    "bandnews fm": "https://stream.zeno.fm/dn0fsg5s5ceuv",
    "mix fm": "https://stream.zeno.fm/4r6t3g0v7g8uv",
    "transamerica": "https://stream.zeno.fm/5q0v0v5a7g8uv",
    "nativa fm": "https://stream.zeno.fm/6r1w1w6b8h9vw",
    "alpha fm": "https://stream.zeno.fm/0v5a5a0f2l3za",
    "nova brasil fm": "https://stream.zeno.fm/1w6b6b1g3m4ab",
    "band fm": "https://stream.zeno.fm/2x7c7c2h4n5bc",
    "eldorado fm": "https://stream.zeno.fm/4z9e9e4j6p7de",
    "radio globo": "https://stream.zeno.fm/7c2h2h7m9s0gh"
}

@tool
def busca_web(query: str) -> str:
    """USE PARA: Notícias atuais, fatos históricos, classificações de futebol ou informações gerais da internet."""
    return search.run(query)

@tool
def clima(cidade: str) -> str:
    """Obtém a temperatura e clima atual de uma cidade específica."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade}&count=1&language=pt&format=json"
        geo_data = json.loads(urllib.request.urlopen(geo_url).read())
        
        if "results" not in geo_data or not geo_data["results"]:
            return f"Não encontrei a cidade '{cidade}'. Por favor, especifique o estado ou país."
        
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        nome_real = geo_data["results"][0]["name"]
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_data = json.loads(urllib.request.urlopen(weather_url).read())
        temp = weather_data['current_weather']['temperature']
        
        return f"O clima atual em {nome_real} é de {temp}°C."
    except Exception as e:
        return f"Erro ao buscar o clima: {e}"

@tool
def cotacao_financeira(ativo: str) -> str:
    """Consulta a cotação atual de moedas (USD, EUR) ou criptomoedas (BTC, ETH) em Real (BRL)."""
    try:
        ativo_upper = ativo.upper().strip()
        pares = {
            "USD": "USD-BRL", "DOLAR": "USD-BRL", "DÓLAR": "USD-BRL",
            "EUR": "EUR-BRL", "EURO": "EUR-BRL",
            "BTC": "BTC-BRL", "BITCOIN": "BTC-BRL",
            "ETH": "ETH-BRL", "ETHEREUM": "ETH-BRL"
        }
        par = pares.get(ativo_upper, f"{ativo_upper}-BRL")
        url = f"https://economia.awesomeapi.com.br/last/{par}"
        data = json.loads(urllib.request.urlopen(url).read())
        
        chave = par.replace("-", "")
        valor = data[chave]["bid"]
        variacao = data[chave]["pctChange"]
        
        return f"Cotação atual de {ativo_upper}: R$ {valor} (Variação do dia: {variacao}%)"
    except Exception as e:
        return f"Não foi possível buscar a cotação de {ativo}."

@tool
def consultar_loteria(tipo_loteria: str) -> str:
    """Consulta resultados de loterias oficiais (Mega-Sena, Lotofácil, Quina) ou Jogo do Bicho. 
    DICA: Para o Jogo do Bicho, especifique o estado para melhor precisão (ex: 'Jogo do Bicho RJ hoje', 'Jogo do Bicho MG')."""
    try:
        query = f"resultado {tipo_loteria} ultimo sorteio ou apuração de hoje"
        resultado = search.run(query)
        return f"Resultado da busca para '{tipo_loteria}':\n{resultado}"
    except Exception as e:
        return f"Erro ao buscar loteria: {e}"

board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None

@tool
def jogar_xadrez(move: str) -> str:
    """Joga um movimento de xadrez. USE QUANDO o usuário quiser jogar xadrez ou enviar um lance (ex: 'e4', 'Nf3')."""
    global board, engine
    try:
        board.push_san(move)
        if board.is_game_over():
            res = f"Fim de jogo! Resultado: {board.result()}"
            board.reset()
            return res
        
        if engine:
            bot_move = engine.play(board, chess.engine.Limit(time=0.5)).move
        else:
            import random
            bot_move = random.choice(list(board.legal_moves))
            
        board.push(bot_move)
        return f"Você jogou {move}. Eu respondi com {bot_move.uci()}. Sua vez!"
    except Exception as e:
        return f"Movimento inválido: {e}. Tente 'e4' ou 'Nf3'."

@tool
def tocar_radio(nome_radio: str) -> str:
    """Toca uma rádio específica. USE QUANDO o usuário pedir para ouvir uma RÁDIO ao vivo."""
    try:
        nome_lower = nome_radio.lower()
        for radio_key, stream_url in RADIOS_BRASIL.items():
            if radio_key in nome_lower:
                return f"LINK_RADIO_ENCONTRADO:{nome_radio}:{stream_url}"
        
        query = f"link direto stream ao vivo rádio {nome_radio} .mp3 OR .aac OR .m3u8"
        resultado = search.run(query)
        links = re.findall(r'https?://\S+', resultado)
        
        if links:
            return f"LINK_RADIO_ENCONTRADO:{nome_radio}:{links[0]}"
        else:
            return f"Não encontrei um link de streaming para {nome_radio}."
    except Exception as e:
        return f"Erro ao buscar rádio: {e}"

@tool
def tocar_musica_youtube(musica: str) -> str:
    """Toca uma música, banda ou clipe no YouTube. USE QUANDO o usuário pedir para ouvir uma MÚSICA ou ARTISTA."""
    try:
        query = f"site:youtube.com {musica} official OR lyric OR audio"
        resultado = search.run(query)
        youtube_urls = re.findall(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', resultado)
        
        if youtube_urls:
            return f"LINK_YOUTUBE_ENCONTRADO:{musica}:{youtube_urls[0]}"
        else:
            query2 = f"youtube {musica}"
            resultado2 = search.run(query2)
            youtube_urls2 = re.findall(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', resultado2)
            
            if youtube_urls2:
                return f"LINK_YOUTUBE_ENCONTRADO:{musica}:{youtube_urls2[0]}"
            else:
                return f"Não encontrei '{musica}' no YouTube."
    except Exception as e:
        return f"Erro ao buscar no YouTube: {e}"

# PROMPT DO SISTEMA REFORÇADO
SYSTEM_PROMPT = """Você é um assistente de IA avançado, preciso e útil. 
REGRAS ABSOLUTAS (NUNCA INVENTE INFORMAÇÕES):
1. CLIMA: Use 'clima' para tempo/temperatura de uma cidade.
2. FINANÇAS: Use 'cotacao_financeira' para Dólar, Euro, Bitcoin, etc.
3. LOTERIAS E JOGO DO BICHO: Use SEMPRE 'consultar_loteria' para Mega-Sena, Lotofácil, Quina ou Jogo do Bicho.
4. ESPORTES/FUTEBOL: Use 'busca_web' para resultados de jogos, classificações ou fatos históricos do esporte.
5. NOTÍCIAS E HISTÓRIA: Use 'busca_web' para notícias atuais ou eventos históricos.
6. MÚSICA: Use 'tocar_musica_youtube' para músicas, bandas ou clipes.
7. RÁDIO: Use 'tocar_radio' para rádios ao vivo.
8. XADREZ: Use 'jogar_xadrez' para lances (ex: 'e4').

Se o usuário perguntar sobre loteria ou bicho, acione a ferramenta 'consultar_loteria' imediatamente.
Responda de forma direta, natural e em português."""

llm_with_tools = llm.bind_tools([busca_web, clima, cotacao_financeira, consultar_loteria, jogar_xadrez, tocar_radio, tocar_musica_youtube])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.message}
        ]
        
        response = llm_with_tools.invoke(messages)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call['args']
            
            if name == "busca_web":
                result = busca_web.invoke(args)
            elif name == "clima":
                result = clima.invoke(args)
            elif name == "cotacao_financeira":
                result = cotacao_financeira.invoke(args)
            elif name == "consultar_loteria":
                result = consultar_loteria.invoke(args)
            elif name == "jogar_xadrez":
                result = jogar_xadrez.invoke(args)
            elif name == "tocar_radio":
                result = tocar_radio.invoke(args)
            elif name == "tocar_musica_youtube":
                result = tocar_musica_youtube.invoke(args)
            else:
                result = "Ferramenta desconhecida."
            
            messages.append(response)
            messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call['id']})
            final_response = llm_with_tools.invoke(messages)
            return {"reply": final_response.content}
        else:
            return {"reply": response.content}
            
    except Exception as e:
        return {"reply": f"Erro no servidor: {str(e)}"}
