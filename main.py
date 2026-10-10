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

# TROCANDO O CÉREBRO PARA O MODELO 70B (MUITO MAIS INTELIGENTE E OBEDIENTE)
llm = ChatGroq(
    temperature=0.1, # Levemente maior para criatividade, mas ainda preciso
    model_name="openai/gpt-oss-120b", 
    groq_api_key=os.environ.get("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")
)

search = DuckDuckGoSearchRun()

@tool
def cotacao(ativo: str) -> str:
    """Use ESTA FERRAMENTA SEMPRE que o usuário perguntar sobre: dólar, real, euro, bitcoin, criptomoedas, cotação ou valor de qualquer moeda."""
    try:
        ativo_clean = ativo.upper().strip().replace("DÓLAR", "DOLAR").replace("REAL", "BRL")
        pares = {"USD": "USD-BRL", "DOLAR": "USD-BRL", "BRL": "USD-BRL", "EUR": "EUR-BRL", "EURO": "EUR-BRL", "BTC": "BTC-BRL", "BITCOIN": "BTC-BRL", "ETH": "ETH-BRL"}
        par = pares.get(ativo_clean, f"{ativo_clean}-BRL")
        url = f"https://economia.awesomeapi.com.br/last/{par}"
        data = json.loads(urllib.request.urlopen(url).read())
        chave = par.replace("-", "")
        return f"A cotação atual de {ativo_clean} é R$ {data[chave]['bid']} (Variação de {data[chave]['pctChange']}% hoje)."
    except Exception as e:
        return f"Erro ao buscar cotação. Tente 'USD', 'EUR' ou 'BTC'."

@tool
def clima(cidade: str) -> str:
    """Use ESTA FERRAMENTA SEMPRE que o usuário perguntar sobre: tempo, temperatura, chuva ou clima de qualquer cidade."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cidade}&count=1&language=pt&format=json"
        geo_data = json.loads(urllib.request.urlopen(geo_url).read())
        if "results" not in geo_data or not geo_data["results"]:
            return f"Não encontrei a cidade '{cidade}'. Tente escrever o nome corretamente."
        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
        nome_real = geo_data["results"][0]["name"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_data = json.loads(urllib.request.urlopen(weather_url).read())
        return f"A temperatura atual em {nome_real} é de {weather_data['current_weather']['temperature']}°C."
    except Exception as e:
        return f"Erro ao buscar clima: {e}"

@tool
def loteria(tipo: str) -> str:
    """Use ESTA FERRAMENTA SEMPRE que o usuário perguntar sobre: Mega-Sena, Lotofácil, Quina, Jogo do Bicho ou resultados de sorteio."""
    try:
        return search.invoke(f"ultimo resultado {tipo} sorteio apuração oficial")
    except Exception as e:
        return f"Erro ao buscar loteria: {e}"

@tool
def busca_web(query: str) -> str:
    """Use ESTA FERRAMENTA SEMPRE que o usuário perguntar sobre: futebol, notícias, fatos históricos ou qualquer informação que não seja clima, cotação ou loteria."""
    return search.invoke(query)

board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None

@tool
def xadrez(move: str) -> str:
    """Use ESTA FERRAMENTA para jogar xadrez. Recebe lances como 'e4', 'Nf3', 'O-O'."""
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

@tool
def radio(nome: str) -> str:
    """Use ESTA FERRAMENTA para tocar rádios ao vivo (Jovem Pan, CBN, Antena 1)."""
    radios = {"jovem pan": "https://stream.zeno.fm/yn65fsaurfhvv", "cbn": "https://n008a-eu.rcs.revma.com/ypqt40u0x1zuv", "antena 1": "https://antena1.stream.com.br/antena1"}
    for k, v in radios.items():
        if k in nome.lower(): return f"LINK_RADIO_ENCONTRADO:{nome}:{v}"
    links = re.findall(r'https?://\S+', search.invoke(f"stream ao vivo rádio {nome} .mp3 OR .m3u8"))
    return f"LINK_RADIO_ENCONTRADO:{nome}:{links[0]}" if links else f"Rádio {nome} não encontrada."

@tool
def youtube(musica: str) -> str:
    """Use ESTA FERRAMENTA para tocar músicas, bandas ou clipes no YouTube."""
    links = re.findall(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', search.invoke(f"site:youtube.com {musica}"))
    return f"LINK_YOUTUBE_ENCONTRADO:{musica}:{links[0]}" if links else f"Não achei '{musica}' no YouTube."

# Vincula as ferramentas ao modelo 70B
llm_with_tools = llm.bind_tools([cotacao, clima, loteria, busca_web, xadrez, radio, youtube])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        # Prompt curto, direto e sem contradições
        system_prompt = "Você é um assistente útil. USE AS FERRAMENTAS fornecidas para responder. NUNCA diga que não sabe ou que não tem acesso a dados. Se a pergunta for sobre moedas, use 'cotacao'. Se for sobre tempo, use 'clima'."
        
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
