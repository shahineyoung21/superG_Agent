import os
import yfinance as yf
import pandas as pd
import requests
import google.generativeai as genai

# 1. تهيئة Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing in Secrets!")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro')

# --- Tool 1: إرسال إشعارات لتليجرام بدون أخطاء تنسيق ---
def send_telegram_message(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message} # بدون parse_mode لتفادي أخطاء الماركداون
        try:
            res = requests.post(url, json=payload, timeout=10)
            print(f"Telegram Status: {res.status_code}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
    else:
        print("Telegram configuration missing.")

# --- Tool 2: جلب بيانات السوق المضمونة (yfinance) ---
def fetch_advanced_market_data(symbol="BTC-USD"):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="7d", interval="1h")

    if df.empty:
        raise RuntimeError("Could not fetch market data from Yahoo Finance!")

    df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)

    # حساب RSI مع حماية القسمة على صفر
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))

    # المتوسطات والمؤشرات
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # حماية من أي قيم مفقودة (NaN) لمنع أخطاء التنسيق
    df = df.fillna(0)

    return df.iloc[-1]

# --- Tool 3: قراءة الذاكرة ---
def read_agent_memory():
    if os.path.exists("agent_log.txt"):
        with open("agent_log.txt", "r", encoding="utf-8") as f:
            logs = f.readlines()
            return "".join(logs[-20:])
    return "بداية سجل جديد."

# --- المحرك الرئيسي ---
def run_super_agent():
    data = fetch_advanced_market_data()
    past_memory = read_agent_memory()

    prompt = f"""
    أنت Super-Agent خبير في التحليل الفني وإدارة مخاطر التداول.
    
    [سجل الذاكرة والقرارات السابقة]:
    {past_memory}
    
    [بيانات السوق الفنية اللحظية لـ BTC/USDT]:
    - السعر الحالي: {data['close']:.2f}
    - مؤشر RSI (14): {data['RSI']:.2f}
    - المتوسط المتحرك SMA 20: {data['SMA_20']:.2f}
    - المتوسط المتحرك SMA 50: {data['SMA_50']:.2f}
    - مؤشر MACD: {data['MACD']:.2f} (خط الإشارة: {data['Signal_Line']:.2f})

    قم بتنفيذ التحليل بناءً على سير العمل التالي:
    1. مراجعة الذاكرة والتقييم الذاتي.
    2. التحليل الفني المركب.
    3. القرار النهائي (شراء / بيع / انتظار) مع تحديد مستويات وقف الخسارة.
    4. التحديث الذاتي للدورة القادمة.
    """

    response = model.generate_content(prompt)
    report = response.text

    print("=== Execution Complete ===")
    print(report)

    # حفظ التقرير في ملف الذاكرة المحلي
    with open("agent_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- [Log Step] Price: {data['close']:.2f} | RSI: {data['RSI']:.2f} ---\n" + report + "\n")

    # إرسال التقرير لتليجرام مجزأ (لتفادي حظر الطول الأقصى للرسالة)
    full_text = f"🤖 Super-Agent Report\n💰 Price: {data['close']:.2f}\n📈 RSI: {data['RSI']:.2f}\n\n{report}"
    for i in range(0, len(full_text), 3900):
        send_telegram_message(full_text[i:i+3900])

if __name__ == "__main__":
    run_super_agent()
