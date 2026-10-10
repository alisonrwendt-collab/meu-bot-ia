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
    groq_api_key=os.environ.get("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")
)

search = DuckDuckGoSearchRun()

@tool
def busca_web(query: str) -> str:
    """USE OBRIGATORIAMENTE para: Notícias atuais, fatos históricos, resultados de futebol e classificações."""
    return search.run(query)

@tool
def clima(cidade: str) -> str:
    """USE OBRIGATORIAMENTE para: Previsão do tempo e temperatura de qualquer cidade."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade}&count=1&language=pt&format=json"
        geo_data = json.loads(urllib.request.urlopen(geo_url).read())
        if "results" not in geo_data or not geo_data["results"]:
            return f"Cidade '{cidade}' não encontrada."
        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
        nome_real = geo_data["results"][0]["name"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_data = json.loads(urllib.request.urlopen(weather_url).read())
        return f"Clima em {nome_real}: {weather_data['current_weather']['temperature']}°C"
    except Exception as e:
        return f"Erro no clima: {e}"

@tool
def cotacao(ativo: str) -> str:
    """USE OBRIGATORIAMENTE ESTA FERRAMENTA quando o usuário mencionar: dólar, real, euro, bitcoin, criptomoedas, cotação ou valor da moeda. O argumento 'ativo' deve ser a moeda (ex: 'USD', 'BTC', 'Dolar', 'Euro')."""
    try:
        ativo_clean = ativo.upper().strip().replace("DÓLAR", "DOLAR")
        pares = {"USD": "USD-BRL", "DOLAR": "USD-BRL", "EUR": "EUR-BRL", "EURO": "EUR-BRL", "BTC": "BTC-BRL", "BITCOIN": "BTC-BRL", "ETH": "ETH-BRL"}
        par = pares.get(ativo_clean, f"{ativo_clean}-BRL")
        url = f"https://economia.awesomeapi.com.br/last/{par}"
        data = json.loads(urllib.request.urlopen(url).read())
        chave = par.replace("-", "")
        return f"Cotação de {ativo_clean}: R$ {data[chave]['bid']} (Variação: {data[chave]['pctChange']}%)"
    except Exception as e:
        return f"Erro ao buscar cotação. Tente usar 'USD', 'EUR' ou 'BTC'."

@tool
def loteria(tipo: str) -> str:
    """USE OBRIGATORIAMENTE para: Resultados da Mega-Sena, Lotofácil, Quina ou Jogo do Bicho."""
    try:
        return search.run(f"ultimo resultado {tipo} sorteio apuração")
    except Exception as e:
        return f"Erro ao buscar loteria: {e}"

board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None

@tool
def xadrez(move: str) -> str:
    """USE OBRIGATORIAMENTE para: Jogar xadrez. Recebe lances como 'e4', 'Nf3', 'O-O'."""
    global board, engine
    try:
        board.push_san(move)
        if board.is_game_over():
            res = f"Fim de jogo! {board.result()}"
            board.reset()
            return res
        bot_move = engine.play(board, chess.engine.Limit(time=0.5)).move if engine else list(board.legal_moves)[0]
        board.push(bot_move)
        return f"Você jogou {move}. Eu respondi com {bot_move.uci()}. Sua vez!"
    except Exception as e:
        return f"Lance inválido. Tente 'e4' ou 'Nf3'."

@tool
def radio(nome: str) -> str:
    """USE OBRIGATORIAMENTE para: Tocar rádios ao vivo (Jovem Pan, CBN, Antena 1)."""
    radios = {"jovem pan": "https://stream.zeno.fm/yn65fsaurfhvv", "cbn": "https://n008a-eu.rcs.revma.com/ypqt40u0x1zuv", "antena 1": "https://antena1.stream.com.br/antena1"}
    for k, v in radios.items():
        if k in nome.lower(): return f"LINK_RADIO_ENCONTRADO:{nome}:{v}"
    links = re.findall(r'https?://\S+', search.run(f"stream ao vivo rádio {nome} .mp3 OR .m3u8"))
    return f"LINK_RADIO_ENCONTRADO:{nome}:{links[0]}" if links else f"Rádio {nome} não encontrada."

@tool
def youtube(musica: str) -> str:
    """USE OBRIGATORIAMENTE para: Tocar músicas, bandas ou clipes no YouTube."""
    links = re.findall(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', search.run(f"site:youtube.com {musica}"))
    return f"LINK_YOUTUBE_ENCONTRADO:{musica}:{links[0]}" if links else f"Não achei '{musica}' no YouTube."

llm_with_tools = llm.bind_tools([busca_web, clima, cotacao, loteria, xadrez, radio, youtube])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        # PROMPT RÍGIDO QUE PROÍBE O BOT DE DIZER QUE "NÃO SABE"
        system_prompt = """Você é um assistente que USA FERRAMENTAS para tudo. 
        REGRAS ABSOLUTAS (NUNCA QUEBRE):
        1. Se o usuário falar em DÓLAR, REAL, EURO, BITCOIN ou COTAÇÃO, você DEVE usar a ferramenta `cotacao`. NUNCA diga que não tem acesso a dados em tempo real.
        2. Se falar em CLIMA, use `clima`.
        3. Se falar em LOTERIA ou JOGO DO BICHO, use `loteria`.
        4. Se falar em FUTEBOL ou NOTÍCIAS, use `busca_web`.
        NUNCA invente dados. Use a ferramenta correta."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.message}
        ]
        
        response = llm_with_tools.invoke(messages)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call['args']
            
            tools_map = {
                "busca_web": busca_web, "clima": clima, "cotacao": cotacao,
                "loteria": loteria, "xadrez": xadrez, "radio": radio, "youtube": youtube
            }
            
            # Executa a ferramenta de forma segura
            tool_func = tools_map.get(name, lambda x: "Ferramenta desconhecida")
            result = tool_func(args)
            
            messages.append(response)
            messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call['id']})
            final_response = llm_with_tools.invoke(messages)
            return {"reply": final_response.content}
        else:
            return {"reply": response.content}
            
    except Exception as e:
        return {"reply": f"Erro interno: {str(e)}"}
