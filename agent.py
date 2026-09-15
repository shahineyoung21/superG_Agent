import os
import ccxt
import pandas as pd
import requests
import google.generativeai as genai

# 1. التحقق من وجود مفتاح Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing in Secrets!")

genai.configure(api_key=api_key)

# قائمة موديلات Gemini بالترتيب (fallback) - لو موديل اتلغى أو مش متاح، بيجرب اللي بعده
MODEL_CANDIDATES = ['gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash']

# --- Tool 1: إرسال إشعارات لتليجرام ---
def send_telegram_message(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
