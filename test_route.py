import asyncio
from backend.routes.ads import generate_new_ad
from backend.schemas import URLInput
from backend.models import User
from backend.db import SessionLocal

async def main():
    db = SessionLocal()
    user = db.query(User).first()
    if not user:
        print("No user found!")
        return
    input_data = URLInput(url="https://test.com", voice_backend="chatterbox")
    try:
        res = await generate_new_ad(input_data, user, db)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
