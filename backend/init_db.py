import os
import sys
from models import Base
from db import get_engine

engine = get_engine()
Base.metadata.create_all(engine)
print("Database tables created successfully.")
