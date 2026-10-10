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

# Modelo ativo e gratuito da Groq em 2026
llm = ChatGroq(
    temperature=0,
    model_name="openai/gpt-oss-20b",
    groq_api_key=os.environ.get("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")
)

search = DuckDuckGoSearchRun()

@tool
def busca_web(query: str) -> str:
    """Busca informações atuais na internet, como resultados de jogos, notícias ou links."""
    return search.run(query)

@tool
def clima(cidade: str) -> str:
    """Obtém a temperatura atual de uma cidade (ex: 'São Paulo', 'Rio de Janeiro')."""
    # Nota: Para simplificar, usa coordenadas de SP como padrão. 
    # Em uma versão avançada, usaríamos uma API de geocoding.
    lat, lon = "-23.55", "-46.63" 
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        data = json.loads(urllib.request.urlopen(url).read())
        return f"Temperatura em {cidade}: {data['current_weather']['temperature']}°C"
    except:
        return "Não foi possível obter o clima no momento."

board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None

@tool
def jogar_xadrez(move: str) -> str:
    """Joga um movimento de xadrez. Use notação algébrica (ex: 'e4', 'Nf3', 'O-O')."""
    global board, engine
    try:
        board.push_san(move)
        if board.is_game_over():
            res = f"Fim de jogo! Resultado: {board.result()}"
            board.reset() # Reinicia para um novo jogo
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
    """Busca o link de streaming ao vivo de uma rádio específica (ex: 'Jovem Pan', 'CBN', 'Antena 1')."""
    try:
        query = f"link direto stream ao vivo rádio {nome_radio} .mp3 OR .aac OR .m3u8"
        resultado = search.run(query)
        
        # Tenta extrair um link http do resultado
        links = re.findall(r'https?://\S+', resultado)
        
        if links:
            # Pega o primeiro link que parece ser de áudio ou página da rádio
            link_radio = links[0]
            return f"LINK_RADIO_ENCONTRADO:{nome_radio}:{link_radio}"
        else:
            return f"Não encontrei um link de streaming direto para {nome_radio}. Tente buscar o site oficial."
    except Exception as e:
        return f"Erro ao buscar rádio: {e}"

# Vincula TODAS as ferramentas ao modelo
llm_with_tools = llm.bind_tools([busca_web, clima, jogar_xadrez, tocar_radio])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        messages = [
            {"role": "system", "content": "Você é um assistente útil e amigável. Use as ferramentas quando necessário. Responda sempre em português de forma concisa."},
            {"role": "user", "content": req.message}
        ]
        
        # 1ª Chamada: O modelo decide se precisa de uma ferramenta
        response = llm_with_tools.invoke(messages)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call['args']
            
            # Executa a ferramenta escolhida
            if name == "busca_web":
                result = busca_web.invoke(args)
            elif name == "clima":
                result = clima.invoke(args)
            elif name == "jogar_xadrez":
                result = jogar_xadrez.invoke(args)
            elif name == "tocar_radio":
                result = tocar_radio.invoke(args)
            else:
                result = "Ferramenta desconhecida."
            
            # 2ª Chamada: O modelo formula a resposta final com o dado da ferramenta
            messages.append(response)
            messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call['id']})
            final_response = llm_with_tools.invoke(messages)
            return {"reply": final_response.content}
        else:
            # Resposta direta se nenhuma ferramenta for necessária
            return {"reply": response.content}
            
    except Exception as e:
        return {"reply": f"Erro no servidor: {str(e)}"}
