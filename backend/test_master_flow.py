import uuid
from db import SessionLocal, get_engine
from models import Base, Campaign, Brand, Shot, Image, Score, CompetitorAnalysis, AudienceSegment

Base.metadata.create_all(get_engine())

def run_test():
    campaign_id = str(uuid.uuid4())
    db = SessionLocal()
    camp = Campaign(id=campaign_id, business_url="https://example.com", user_id="test_user")
    db.add(camp)
    db.commit()
    db.close()

    print(f"Running Master Flow for campaign: {campaign_id}")
    from jobs import generate_ad
    try:
        result = generate_ad(campaign_id=campaign_id)
        print("Success!", result)
        
        db = SessionLocal()
        brand = db.query(Brand).filter(Brand.campaign_id == campaign_id).first()
        shots = db.query(Shot).filter(Shot.campaign_id == campaign_id).all()
        images = db.query(Image).filter(Image.campaign_id == campaign_id).all()
        score = db.query(Score).filter(Score.campaign_id == campaign_id).first()
        comp = db.query(CompetitorAnalysis).filter(CompetitorAnalysis.campaign_id == campaign_id).first()
        aud = db.query(AudienceSegment).filter(AudienceSegment.campaign_id == campaign_id).first()
        
        print(f"Found Brand: {brand.business if brand else 'None'}")
        print(f"Found Competitor Market Gap: {comp.market_gap if comp else 'None'}")
        print(f"Found Audience Segments: {len(aud.segments) if aud and aud.segments else 0}")
        print(f"Generated {len(shots)} Shots")
        print(f"Generated {len(images)} Images")
        print(f"Final Score: {score.marketing if score else 'None'}")
        db.close()
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    run_test()
