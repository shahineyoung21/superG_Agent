import os
import ccxt
import pandas as pd
import requests
import google.generativeai as genai

# 1. تهيئة النموذج
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

# --- Tool 1: إرسال إشعارات لتليجرام ---
def send_telegram_message(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

# --- Tool 2: جلب البيانات الفنية المتقدمة ---
def fetch_advanced_market_data(symbol="BTC/USDT"):
    exchange = ccxt.binance({'enableRateLimit': True})
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Moving Averages
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df.iloc[-1]

# --- Tool 3: قراءة الذاكرة ---
def read_agent_memory():
    if os.path.exists("agent_log.txt"):
        with open("agent_log.txt", "r", encoding="utf-8") as f:
            logs = f.readlines()
            return "".join(logs[-20:])
    return "لا توجد سجلات سابقة."

# --- المحرك الرئيسي ---
def run_super_agent():
    data = fetch_advanced_market_data()
    past_memory = read_agent_memory()
    
    prompt = f"""
    أنت Super-Agent خبير في التحليل الفني وإدارة مخاطر التداول.
    
    [سجل الذاكرة والقرارات السابقة]:
    {past_memory}
    
    [بيانات السوق الفنية اللحظية لـ BTC/USDT]:
    - السعر الحالي: {data['close']}
    - مؤشر RSI (14): {data['RSI']:.2f}
    - المتوسط المتحرك SMA 20: {data['SMA_20']:.2f}
    - المتوسط المتحرك SMA 50: {data['SMA_50']:.2f}
    - مؤشر MACD: {data['MACD']:.2f} (خط الإشارة: {data['Signal_Line']:.2f})

    قم بتنفيذ التحليل بناءً على سير العمل التالي:
    1. مراجعة الذاكرة والتقييم الذاتي.
    2. التحليل الفني المركب.
    3. القرار النهائي (شراء / بيع / انتظار) مع تحديد مستويات وقف الخسارة وإدارة المخاطر.
    4. التحديث الذاتي للدورة القادمة.
    """
    
    response = model.generate_content(prompt)
    report = response.text
    
    print("=== Advanced Super-Agent Execution Complete ===")
    print(report)
    
    # حفظ في الذاكرة
    with open("agent_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- [Step Log] Price: {data['close']} | RSI: {data['RSI']:.2f} ---\n" + report + "\n")
    
    # إرسال التقرير لتليجرام
    telegram_text = f"🤖 *Super-Agent Report*\n💰 *Price:* {data['close']}\n📈 *RSI:* {data['RSI']:.2f}\n\n{report}"
    send_telegram_message(telegram_text[:4000]) # تحديد الحد الأقصى للرسالة

if __name__ == "__main__":
    run_super_agent()
