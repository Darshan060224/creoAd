"""
Day 1 — Brand Agent
Model: qwen3:32b (we'll use settings.ollama_model as fallback, but prompt specified qwen3:32b)
"""
import requests, json, uuid
try:
    from ..config import settings
    from ..db import SessionLocal
    from ..models import BrandMemory
except ImportError:
    from config import settings
    from db import SessionLocal
    from models import BrandMemory

from schemas.agent_schemas import BrandOutput

def analyze_brand(brand_data: dict, job_id: str = None, user_id: str = None, model_name: str = "qwen3:32b") -> dict:
    brand_memory_context = ""
    brand_name = brand_data.get('name', '').strip()
    session = SessionLocal()
    brand_memory = None
    
    # Fetch existing Brand Memory
    if user_id and brand_name:
        brand_memory = session.query(BrandMemory).filter_by(user_id=user_id, brand_name=brand_name).first()
        if brand_memory and brand_memory.json_state:
            brand_memory_context = f"\n\nPermanent Brand Memory (MUST Align With This):\n{json.dumps(brand_memory.json_state, indent=2)}\n\nDo not contradict established brand identity."

    prompt = f"""You are a senior brand strategist.

Analyze the business information. {brand_memory_context}

Business: {brand_name}
Description: {brand_data.get('description', '')[:500]}
Tagline: {brand_data.get('tagline', '')}
URL: {brand_data.get('url')}

Extract:
- business_type
- target_audience
- unique_selling_points
- tone
- brand_personality
- customer_pain_points
- desired_customer_outcomes

Return valid JSON only.

Schema:
{{
  "business_type":"",
  "target_audience":"",
  "unique_selling_points":[],
  "tone":"",
  "brand_personality":"",
  "customer_pain_points":[],
  "desired_outcomes":[]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        # Validate through Pydantic
        output = BrandOutput.model_validate_json(raw)
        result_dict = output.model_dump()
        
        # Save or update permanent brand memory
        if user_id and brand_name:
            if not brand_memory:
                brand_memory = BrandMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    brand_name=brand_name,
                    json_state={}
                )
                session.add(brand_memory)
            # Merge state
            brand_memory.json_state = {**(brand_memory.json_state or {}), **result_dict}
            session.commit()
            
        session.close()
        return {**brand_data, **result_dict, "analyzed": True}
    except Exception as e:
        session.close()
        print(f"Brand Analyst Error: {e}")
        # Return fallback
        return {
            **brand_data,
            "business_type": "Unknown",
            "target_audience": "General",
            "unique_selling_points": [brand_data.get("tagline", "")],
            "tone": "Professional",
            "brand_personality": "Reliable",
            "customer_pain_points": [],
            "desired_outcomes": []
        }
