from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
import os, chess, chess.engine, urllib.request, json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://meuchatia.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = ChatGroq(
    temperature=0,
    model_name="llama3-70b-8192",
    groq_api_key=os.environ.get("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")
)

search = DuckDuckGoSearchRun()

@tool
def busca_web(query: str) -> str:
    """Busca informações atuais na internet, como resultados de jogos ou rádios."""
    return search.run(query)

@tool
def clima(cidade: str) -> str:
    """Obtém a temperatura atual de uma cidade."""
    lat, lon = "-23.55", "-46.63" # Exemplo: São Paulo
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        data = json.loads(urllib.request.urlopen(url).read())
        return f"Temperatura em {cidade}: {data['current_weather']['temperature']}°C"
    except:
        return "Não foi possível obter o clima."

board = chess.Board()
try:
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
except:
    engine = None # Fallback caso o stockfish demore a carregar

@tool
def jogar_xadrez(move: str) -> str:
    """Joga um movimento de xadrez. Use notação algébrica (ex: 'e4', 'Nf3')."""
    global board, engine
    try:
        board.push_san(move)
        if board.is_game_over():
            res = f"Fim de jogo! Resultado: {board.result()}"
            board.reset() # Reinicia o tabuleiro para um novo jogo
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

# Vincula as ferramentas ao modelo de forma moderna
llm_with_tools = llm.bind_tools([busca_web, clima, jogar_xadrez])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        messages = [
            {"role": "system", "content": "Você é um assistente útil. Use as ferramentas quando necessário. Responda sempre em português."},
            {"role": "user", "content": req.message}
        ]
        
        # Primeira chamada: o modelo decide se precisa de uma ferramenta
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
            else:
                result = "Ferramenta desconhecida."
            
            # Segunda chamada: o modelo formula a resposta final com o dado da ferramenta
            messages.append(response)
            messages.append({"role": "tool", "content": str(result), "tool_call_id": tool_call['id']})
            final_response = llm_with_tools.invoke(messages)
            return {"reply": final_response.content}
        else:
            # Resposta direta se nenhuma ferramenta for necessária
            return {"reply": response.content}
            
    except Exception as e:
        return {"reply": f"Erro no servidor: {str(e)}"}
