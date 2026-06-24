"""
6. Campaign Knowledge Graph Agent
"""
import requests, json
from config import settings
from schemas.advanced_agent_schemas import CampaignKnowledgeGraphOutput

def generate_knowledge_graph(campaign_data: dict, model_name: str = "deepseek-r1") -> dict:
    prompt = f"""You are a Marketing Intelligence Analyst.

Analyze relationships between:
Brand
Audience
Offer
Campaign
Creative
Performance

Campaign Data:
{json.dumps(campaign_data, indent=2)}

Create a structured relationship map.

Return JSON only matching exactly this format:
{{
  "nodes":[
    {{"id": "node_id", "type": "Brand/Audience/etc", "properties": {{}}}}
  ],
  "relationships":[
    {{"source": "node_id", "target": "node_id", "relation_type": "TARGETS/OFFERS/etc"}}
  ]
}}"""

    r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
        "model": getattr(settings, "ollama_model", model_name),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.5}
    }, timeout=settings.ollama_request_timeout)

    try:
        raw = r.json().get("response", "")
        output = CampaignKnowledgeGraphOutput.model_validate_json(raw)
        return output.model_dump()
    except Exception as e:
        print(f"Knowledge Graph Agent Error: {e}")
        return {"nodes": [], "relationships": []}
