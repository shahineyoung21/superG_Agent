import os
import ccxt
import pandas as pd
import requests

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY is missing in Secrets!")

MODEL_CANDIDATES = ['openai/gpt-5.2', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.0-flash']

def send_telegram_message(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload)
            print(f"Telegram status code: {res.status_code}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
    else:
        print("Telegram tokens are missing, skipping notification.")

def fetch_advanced_market_data(symbol="BTC/USDT"):
    exchanges = [
        ccxt.kucoin({'enableRateLimit': True}),
        ccxt.bybit({'enableRateLimit': True}),
        ccxt.kraken({'enableRateLimit': True})
    ]
    bars = None
    for ex in exchanges:
        try:
            fetch_symbol = "BTC/USD" if ex.id == 'kraken' and symbol == "BTC/USDT" else symbol
            bars = ex.fetch_ohlcv(fetch_symbol, timeframe='1h', limit=100)
            if bars:
                break
        except Exception as e:
            print(f"Failed with {ex.id}: {e}")
            continue
    if not bars:
        raise RuntimeError("Could not fetch market data from any exchange!")
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df.iloc[-1]

def read_agent_memory():
    if os.path.exists("agent_log.txt"):
        with open("agent_log.txt", "r", encoding="utf-8") as f:
            logs = f.readlines()
            return "".join(logs[-20:])
    return "بداية سجل جديد."

def generate_with_fallback(prompt):
    last_error = None
    for model_name in MODEL_CANDIDATES:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model_name, "messages": [{"role": "user", "content": prompt}]}
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            last_error = e
            continue
    raise RuntimeError(f"Could not generate content with any OpenRouter model! Last error: {last_error}")

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
    3. القرار النهائي (شراء / بيع / انتظار) مع تحديد مستويات وقف الخسارة.
    4. التحديث الذاتي للدورة القادمة.
    """
    report = generate_with_fallback(prompt)
    print(report)
    with open("agent_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- [Step Log] Price: {data['close']} | RSI: {data['RSI']:.2f} ---\n" + report + "\n")
    telegram_text = f"🤖 *Super-Agent Report*\n💰 *Price:* {data['close']}\n📈 *RSI:* {data['RSI']:.2f}\n\n{report}"
    send_telegram_message(telegram_text[:4000])

if __name__ == "__main__":
    try:
        run_super_agent()
    except Exception as e:
        print(f"Agent run failed: {e}")
        send_telegram_message(f"⚠️ *Super-Agent Failed*\n{e}")
        raise