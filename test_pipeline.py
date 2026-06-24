import time
from backend.jobs import generate_ad

if __name__ == "__main__":
    start = time.time()
    generate_ad(campaign_id="test_camp", url="https://example.com", job_id="test_job")
    print(f"Total time: {time.time() - start}")
