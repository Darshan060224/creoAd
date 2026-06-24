import sys
import os
import json

from agents.advanced.autonomous_qa import evaluate_and_repair

bad_ad = {
    "brand": "Tech Gadgets Co",
    "target_audience": "Everyone",
    "hook": "We sell gadgets.",
    "cta": "Buy our stuff.",
    "visual_quality": "Boring static images of phones.",
    "emotional_impact": "None",
    "retention_potential": "Low"
}

print("Running Autonomous QA Agent Evaluation Loop...")
print("Input Ad Data:")
print(json.dumps(bad_ad, indent=2))
print("\n---\n")

result = evaluate_and_repair(bad_ad, model_name="qwen3:32b", max_iterations=2)

print("\n--- FINAL QA OUTPUT ---")
print(json.dumps(result, indent=2))
