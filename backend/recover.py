import json

log_paths = [
    "/home/da24/.gemini/antigravity-ide/brain/27221a4a-781d-4230-a00d-471ea0c71fe3/.system_generated/logs/transcript.jsonl",
    "/home/da24/.gemini/antigravity-ide/brain/262827d5-a360-4bb8-a809-378e1a0e7c6a/.system_generated/logs/transcript.jsonl"
]

for p in log_paths:
    try:
        with open(p, "r") as f:
            for line in f:
                if "def _generate_voiceover_with_fallback" in line or "def _redis_get" in line:
                    data = json.loads(line)
                    if data.get("type") == "VIEW_FILE" or data.get("type") == "READ_FILE" or data.get("type") == "USER_INPUT":
                        print(f"FOUND IN {p}!")
                        with open("recovered_jobs.txt", "w") as out:
                            out.write(data.get("content", ""))
                        exit(0)
    except Exception as e:
        pass
print("Not found.")
