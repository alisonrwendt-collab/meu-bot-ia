from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
import os, urllib.request, json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MODELO ESTÁVEL COM SUPORTE NATIVO A FERRAMENTAS NA GROQ
llm = ChatGroq(
    temperature=0.1,
    model_name="qwen/qwen3.8-27b, 
    groq_api_key=os.environ.get("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")
)

search = DuckDuckGoSearchRun()

@tool
def cotacao(ativo: str) -> str:
    """Use ESTA FERRAMENTA para saber o valor de moedas (dólar, euro) ou criptomoedas (bitcoin). Exemplo de ativo: 'USD', 'EUR', 'BTC'."""
    try:
        ativo_clean = ativo.upper().strip().replace("DÓLAR", "USD").replace("REAL", "BRL")
        pares = {"USD": "USD-BRL", "EUR": "EUR-BRL", "BTC": "BTC-BRL", "ETH": "ETH-BRL"}
        par = pares.get(ativo_clean, f"{ativo_clean}-BRL")
        url = f"https://economia.awesomeapi.com.br/last/{par}"
        data = json.loads(urllib.request.urlopen(url).read())
        chave = par.replace("-", "")
        return f"A cotação atual de {ativo_clean} é R$ {data[chave]['bid']} (Variação: {data[chave]['pctChange']}%)."
    except Exception as e:
        return f"Erro ao buscar cotação. Tente 'USD', 'EUR' ou 'BTC'."

@tool
def clima(cidade: str) -> str:
    """Use ESTA FERRAMENTA para saber a temperatura e previsão do tempo de qualquer cidade."""
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
        return f"Erro ao buscar clima: {e}"

@tool
def loteria(tipo: str) -> str:
    """Use ESTA FERRAMENTA para saber resultados da Mega-Sena, Lotofácil, Quina ou Jogo do Bicho."""
    try:
        return search.invoke(f"ultimo resultado {tipo} sorteio apuração oficial")
    except Exception as e:
        return f"Erro ao buscar loteria: {e}"

@tool
def busca_web(query: str) -> str:
    """Use ESTA FERRAMENTA para notícias, futebol, fatos históricos ou qualquer informação geral da internet."""
    return search.invoke(query)

# Vincula apenas as ferramentas essenciais e estáveis
llm_with_tools = llm.bind_tools([cotacao, clima, loteria, busca_web])

class Msg(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: Msg):
    try:
        system_prompt = "Você é um assistente útil e direto. USE AS FERRAMENTAS fornecidas para responder perguntas sobre cotação, clima, loteria ou notícias. NUNCA diga que não sabe ou que não tem acesso a dados. Se a pergunta for sobre moedas, use 'cotacao'. Se for sobre tempo, use 'clima'."
        
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
                "cotacao": cotacao, "clima": clima, "loteria": loteria, "busca_web": busca_web
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
