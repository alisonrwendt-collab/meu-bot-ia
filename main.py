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

# MODELO OFICIAL DA GROQ COM SUPORTE COMPROVADO E ESTÁVEL A FERRAMENTAS
llm = ChatGroq(
    temperature=0.0,
    model_name="openai/gpt-oss-120b", 
    groq_api_key=os.environ.get("GROQ_API_KEY")
)

search = DuckDuckGoSearchRun()

@tool
def cotacao(ativo: str) -> str:
    """Use PARA SABER o valor de moedas (dólar, euro) ou criptomoedas (bitcoin). Ex: 'USD', 'EUR', 'BTC'."""
    try:
        ativo_clean = ativo.upper().strip().replace("DÓLAR", "USD").replace("REAL", "BRL")
        pares = {"USD": "USD-BRL", "EUR": "EUR-BRL", "BTC": "BTC-BRL", "ETH": "ETH-BRL"}
        par = pares.get(ativo_clean, f"{ativo_clean}-BRL")
        url = f"https://economia.awesomeapi.com.br/last/{par}"
        data = json.loads(urllib.request.urlopen(url).read())
        chave = par.replace("-", "")
        return f"A cotação atual de {ativo_clean} é R$ {data[chave]['bid']} (Variação: {data[chave]['pctChange']}%)."
    except Exception as e:
        return f"Erro ao buscar cotação."

@tool
def clima(cidade: str) -> str:
    """Use PARA SABER a temperatura e previsão do tempo de qualquer cidade."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade}&count=1&language=pt&format=json"
        geo_data = json.loads(urllib.request.urlopen(geo_url).read())
        if "results" not in geo_data or not geo_data["results"]:
            return f"Cidade '{cidade}' não encontrada."
        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
        nome_real = geo_data["results"][0]["name"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_data = json.loads(urllib.request.urlopen(weather_url).read())
        return f"A temperatura atual em {nome_real} é de {weather_data['current_weather']['temperature']}°C."
    except Exception as e:
        return f"Erro ao buscar clima."

@tool
def loteria(tipo: str) -> str:
    """Use PARA SABER resultados da Mega-Sena, Lotofácil, Quina ou Jogo do Bicho."""
    try:
        return search.invoke(f"ultimo resultado {tipo} sorteio apuração oficial")
    except Exception as e:
        return f"Erro ao buscar loteria."

@tool
def busca_web(query: str) -> str:
    """Use PARA notícias, futebol, fatos históricos ou qualquer informação geral da internet."""
    return search.invoke(query)

@tool
def xadrez(move: str) -> str:
    """Use PARA JOGAR xadrez. Recebe lances como 'e4', 'Nf3', 'O-O'."""
    global board, engine
    try:
        board.push_san(move)
        if board.is_game_over():
            res = f"Fim de jogo! Resultado: {board.result()}"
            board.reset()
            return res
        bot_move = engine.play(board, chess.engine.Limit(time=0.5)).move if engine else list(board.legal_moves)[0]
        board.push(bot_move)
        return f"Você jogou {move}. Eu respondi com {bot_move.uci()}. Sua vez!"
    except Exception as e:
        return f"Lance inválido. Tente 'e4' ou 'Nf3'."

# Inicializa o tabuleiro global
board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None

@tool
def radio(nome: str) -> str:
    """Use PARA TOCAR rádios ao vivo (Jovem Pan, CBN, Antena 1)."""
    radios = {
        "jovem pan": "https://stream.zeno.fm/yn65fsaurfhvv", 
        "cbn": "https://n008a-eu.rcs.revma.com/ypqt40u0x1zuv", 
        "antena 1": "https://antena1.stream.com.br/antena1"
    }
    for k, v in radios.items():
        if k in nome.lower(): 
            return f"LINK_RADIO_ENCONTRADO:{nome}:{v}"
    links = re.findall(r'https?://\S+', search.invoke(f"stream ao vivo rádio {nome} .mp3 OR .m3u8"))
    return f"LINK_RADIO_ENCONTRADO:{nome}:{links[0]}" if links else f"Rádio {nome} não encontrada."

@tool
def youtube(musica: str) -> str:
    """Use PARA TOCAR músicas, bandas ou clipes no YouTube."""
    links = re.findall(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', search.invoke(f"site:youtube.com {musica}"))
    return f"LINK_YOUTUBE_ENCONTRADO:{musica}:{links[0]}" if links else f"Não achei '{musica}' no YouTube."

# Vincula TODAS as ferramentas ao modelo
tools = [cotacao, clima, loteria, busca_web, xadrez, radio, youtube]
llm_with_tools = llm.bind_tools(tools)

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        # Prompt EXTREMAMENTE DIRETO para forçar o uso de ferramentas
        system_prompt = "VOCÊ É UM ASSISTENTE QUE USA FERRAMENTAS. SE O USUÁRIO PEDIR PARA TOCAR MÚSICA, RÁDIO, JOGAR XADREZ, SABER COTAÇÃO, CLIMA, LOTERIA OU NOTÍCIAS, VOCÊ DEVE USAR A FERRAMENTA CORRESPONDENTE. NUNCA DIGA QUE NÃO PODE FAZER. USE A FERRAMENTA."
        
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
                "cotacao": cotacao, "clima": clima, "loteria": loteria, 
                "busca_web": busca_web, "xadrez": xadrez, "radio": radio, "youtube": youtube
            }
            
            tool_func = tools_map.get(name)
            if tool_func:
                result = tool_func.invoke(args)
            else:
                result = "Ferramenta não encontrada."
            
            messages.append(response)
            messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call['id']})
            final_response = llm_with_tools.invoke(messages)
            return {"reply": final_response.content}
        else:
            return {"reply": response.content}
            
    except Exception as e:
        return {"reply": f"Erro interno: {str(e)}"}
