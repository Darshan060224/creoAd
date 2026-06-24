"""
Performance Predictor (Ad Scoring) Agent
Estimates CTR, Retention, and Conversion before an ad is fully rendered.
"""
import requests, json
try:
    from ...config import settings
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    from config import settings

def score_ad_variant(script: dict, strategy: dict, model_name: str = "qwen3") -> dict:
    prompt = f"""You are an elite Data-Driven Performance Predictor.
Estimate ad performance metrics for this ad variant before it is produced.

Campaign Strategy:
{json.dumps(strategy, indent=2)}

Ad Script / Variant:
{json.dumps(script, indent=2)}

Provide estimated metrics based on the strength of the hook, pacing, and CTA.
Return JSON only matching this format:
{{
  "hook_rate": 45.5,
  "estimated_ctr": 2.1,
  "conversion_score": 8.5,
  "retention_estimate_percent": 65.0,
  "verdict": "Best|Good|Poor"
}}"""
    try:
        r = requests.post(f"{settings.ollama_base_url}/api/generate", json={
            "model": getattr(settings, "ollama_model", model_name),
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=settings.ollama_request_timeout)
        return json.loads(r.json().get("response", ""))
    except Exception as e:
        print(f"Ad Scoring Error: {e}")
        return {
            "hook_rate": 30.0,
            "estimated_ctr": 1.0,
            "conversion_score": 5.0,
            "retention_estimate_percent": 30.0,
            "verdict": "Poor"
        }
