import httpx
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

async def analyze_complaints(complaints_text: str):
    """
    Sends a batch of complaints to OpenRouter (Xiaomi Model)
    and asks for structured insights.
    """
    if not OPENROUTER_API_KEY:
        return {
            "summary": "API Key missing.",
            "top_issues": [],
            "sentiment_score": 0.0,
            "suggested_actions": []
        }

    prompt = f"""
    You are an AI Data Analyst for a smart village system. 
    Analyze the following list of complaints from villagers:
    
    "{complaints_text}"
    
    Provide a JSON response with exactly these fields:
    1. "summary": A 2-sentence summary of the overall situation.
    2. "top_issues": A list of the top 3 most frequent specific problems (e.g., "Broken Pump", "Potholes").
    3. "sentiment_score": A number between -1.0 (Angry) and 1.0 (Happy).
    4. "suggested_actions": A list of 3 concrete actions the government should take immediately.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "xiaomi/mixtral-8x7b-instruct", # Or any specific Xiaomi model you prefer on OpenRouter
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"} # Forces JSON output
            },
            timeout=30.0
        )
    
    if response.status_code == 200:
        import json
        try:
            # Parse the JSON string from the LLM
            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)
        except:
            return None
    return None