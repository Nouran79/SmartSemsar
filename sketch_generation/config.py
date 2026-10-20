import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())      # المفتاح من ملف .env بتاع المشروع لما الفولدر يشتغل لوحده

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  
