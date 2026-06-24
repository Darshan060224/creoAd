"""
Variant Engine
Orchestrates generation of multiple concepts and filters down to the top performers.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.copywriter import write_script
from agents.advanced.ad_scoring import score_ad_variant

def generate_and_filter_variants(
    brand_profile: dict, 
    creative_brief: dict, 
    duration: int, 
    job_id: str, 
    num_variants: int = 10, 
    keep_top_n: int = 3
) -> list:
    """
    Generate `num_variants` ad concepts concurrently.
    Score each using the Performance Predictor.
    Return the top `keep_top_n` scripts.
    """
    variants = []
    
    def generate_single_variant(i):
        # Generate script variation
        script = write_script(brand_profile, creative_brief, duration, job_id)
        # Score the variant
        score = score_ad_variant(script, creative_brief)
        return {"script": script, "score": score}

    with ThreadPoolExecutor(max_workers=min(5, num_variants)) as executor:
        futures = [executor.submit(generate_single_variant, i) for i in range(num_variants)]
        for future in as_completed(futures):
            try:
                res = future.result()
                variants.append(res)
            except Exception as e:
                print(f"Variant Generation Error: {e}")
                
    # Sort variants by conversion_score descending
    sorted_variants = sorted(
        variants, 
        key=lambda x: x.get("score", {}).get("conversion_score", 0), 
        reverse=True
    )
    
    # Return top N scripts
    top_scripts = [v["script"] for v in sorted_variants[:keep_top_n]]
    return top_scripts
