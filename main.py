from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.auth.azure import AzureTokenProvider
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

import requests
import os
import asyncio
from datetime import datetime
import pytz


# =========================================================
# TIME CONTEXT
# =========================================================

india = pytz.timezone("Asia/Kolkata")


def get_time_context():
    now = datetime.now(india)

    return now.strftime(
        "Current local time is %I:%M %p IST on %A, %d %B %Y."
    )


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()

api_key = os.getenv("API_KEY")
azure_endpoint = os.getenv("AZURE_ENDPOINT")
azure_deployment = os.getenv("AZURE_DEPLOYMENT")
model = os.getenv("MODEL")
api_version = os.getenv("API_VERSION")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


# =========================================================
# AUTH
# =========================================================

token_provider = AzureTokenProvider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)


# =========================================================
# MODEL CLIENT
# =========================================================

model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=azure_deployment,
    model=model,
    api_version=api_version,
    azure_endpoint=azure_endpoint,
    api_key=api_key,
)


# =========================================================
# TOOLS
# =========================================================

async def web_search(query: str) -> str:
    """
    Search the web using Tavily API
    """

    try:

        url = "https://api.tavily.com/search"

        headers = {
            "Authorization": f"Bearer {TAVILY_API_KEY}"
        }

        payload = {
            "query": query,
            "max_results": 5,
            "search_depth": "advanced",
            "include_answer": True
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=20
        )

        data = response.json()

        # BEST PART → Tavily AI Answer
        ai_answer = data.get("answer")

        if ai_answer:
            return ai_answer

        results = data.get("results", [])

        if not results:
            return "No relevant information found."

        # fallback summary
        top_result = results[0]

        return f"""
{top_result.get('content', '')}

Source:
{top_result.get('url', '')}
"""

    except Exception as e:
        return f"Web search failed: {str(e)}"
    

async def get_current_datetime() -> str:
    """
    Get current local date and time
    """

    now = datetime.now(india)

    return now.strftime(
        "Today is %A, %d %B %Y. Current time is %I:%M %p IST."
    )


async def get_weather(city: str) -> str:
    """
    Get current weather using WeatherAPI
    """

    try:
        url = (
            f"http://api.weatherapi.com/v1/current.json"
            f"?key={WEATHER_API_KEY}&q={city}"
        )

        response = requests.get(url, timeout=20).json()

        if "current" in response:

            temp = response["current"]["temp_c"]

            condition = response["current"]["condition"]["text"]

            feels_like = response["current"]["feelslike_c"]

            humidity = response["current"]["humidity"]

            wind = response["current"]["wind_kph"]

            return (
                f"Current weather in {city}: "
                f"{temp}°C, {condition}. "
                f"Feels like {feels_like}°C. "
                f"Humidity: {humidity}%. "
                f"Wind Speed: {wind} kph."
            )

        elif "error" in response:
            return f"Weather API Error: {response['error']['message']}"

        return "Weather information is unavailable."

    except Exception as e:
        return f"Weather lookup failed: {str(e)}"


# =========================================================
# AGENTS
# =========================================================

orchestrator_agent = AssistantAgent(
    name="orchestrator_agent",
    model_client=model_client,
    system_message="""
You are an orchestration agent responsible for routing user requests to the most suitable specialized agent.

Routing rules:
- Use 'weather_agent' for weather, temperature, climate, forecast, or location weather queries.
- Use 'greeting_agent' for greetings, introductions, casual openings, or conversational messages.
- Use 'assistant_agent' for:
  - general questions
  - coding
  - reasoning
  - explanations
  - current affairs
  - date/time questions
  - factual queries
  - internet-based queries
  - knowledge questions
  - all other requests

Guidelines:
- Do not answer the user's question directly.
- Only decide which agent should handle the request.
- Return ONLY the agent name.
- If uncertain, prefer 'assistant_agent'.
"""
)


greeting_agent = AssistantAgent(
    name="greeting_agent",
    model_client=model_client,
    description="Greeting Assistant",
    system_message=f"""
You are a friendly conversational assistant.

{get_time_context()}

Respond naturally and politely to:
- greetings
- introductions
- thanks
- casual conversation starters

If appropriate, greet according to the current time naturally.

Keep responses:
- short
- warm
- human-like
- conversational
"""
)


assistant_agent = AssistantAgent(
    name="assistant_agent",
    description="General AI Assistant",
    model_client=model_client,
    tools=[web_search, get_current_datetime],
    system_message="""
You are a helpful, intelligent, and reliable AI assistant.

Provide clear, concise, accurate, and well-structured responses.

When answering:
- Use your existing knowledge whenever sufficient.
- If you are uncertain about an answer, need more accurate information, or the question depends on recent, dynamic, or real-time information, use the available tools.
- Prefer verification instead of assumptions when accuracy matters.
- Think carefully before answering factual or time-sensitive questions.
- When using tools, analyze and summarize information naturally instead of repeating raw tool output.

Behavior guidelines:
- Follow user instructions carefully.
- Maintain a professional, natural, and conversational tone.
- Avoid misleading, fabricated, or unsupported claims.
- Keep responses readable and human-friendly.
- If a request violates safety or ethical guidelines, politely refuse.

Use tools whenever they improve correctness, freshness, or reliability.
"""
)


weather_agent = AssistantAgent(
    name="weather_agent",
    model_client=model_client,
    tools=[get_weather],
    system_message="""
You are a weather information assistant.

Use the available weather tool whenever weather information is needed.

Provide concise, clear, and user-friendly weather responses.
"""
)


# =========================================================
# MAIN ROUTER FUNCTION
# =========================================================

async def run_multi_agent(user_input: str):

    try:

        decision = await orchestrator_agent.run(task=user_input)

        if not decision.messages:
            return "No response from orchestrator."

        decision_text = decision.messages[-1].content.lower().strip()

        print(f"\n[ORCHESTRATOR DECISION]: {decision_text}\n")

        # ---------------- ROUTING ---------------- #

        if "weather_agent" in decision_text:

            result = await weather_agent.run(task=user_input)

        elif "greeting_agent" in decision_text:

            result = await greeting_agent.run(task=user_input)

        else:

            result = await assistant_agent.run(task=user_input)

        # ---------------- FINAL RESPONSE ---------------- #

        if result.messages:

            final_response = result.messages[-1].content

            return final_response

        return "No response generated."

    except Exception as e:

        return f"Application Error: {str(e)}"


# =========================================================
# TERMINAL TEST LOOP
# =========================================================

async def main():

    print("\nMulti-Agent AI Assistant Started")
    print("Type 'exit' to quit.\n")

    while True:

        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        response = await run_multi_agent(user_input)

        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())