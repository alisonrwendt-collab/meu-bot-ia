from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.agents import initialize_agent, Tool, AgentType
from langchain_community.tools import DuckDuckGoSearchRun
import os, chess, chess.engine, urllib.request, json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://meuchatia.netlify.app"],  # Em produção, coloque o domínio do Netlify
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cérebro: Groq (GRÁTIS e rápido!)
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",  # Modelo poderoso e grátis
    groq_api_key=os.environ.get("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") 
)

# Ferramentas
search_tool = DuckDuckGoSearchRun(
    name="BuscaWeb",
    description="Busca resultados de jogos, rádios online e notícias atuais."
)

def get_weather(city: str) -> str:
    # Geocoding simplificado (exemplo para SP)
    lat, lon = "-23.55", "-46.63"
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        data = json.loads(urllib.request.urlopen(url).read())
        return f"Temperatura em {city}: {data['current_weather']['temperature']}°C"
    except:
        return "Não consegui buscar o clima agora."

weather_tool = Tool(name="Clima", func=get_weather, description="Previsão do tempo de uma cidade.")

# Xadrez
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci("stockfish")

def play_chess(move: str) -> str:
    try:
        board.push_san(move)
        if board.is_game_over(): return f"Fim! {board.result()}"
        bot_move = engine.play(board, chess.engine.Limit(time=0.3)).move
        board.push(bot_move)
        return f"Você: {move} | Bot: {bot_move.uci()}"
    except:
        return "Movimento inválido. Use notação como 'e4' ou 'Cf3'."

chess_tool = Tool(name="Xadrez", func=play_chess, description="Joga xadrez. Recebe movimento (ex: 'e4').")

agent = initialize_agent(
    tools=[search_tool, weather_tool, chess_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False
)

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        return {"reply": agent.run(req.message)}
    except Exception as e:
        return {"reply": f"Erro: {str(e)}"}
