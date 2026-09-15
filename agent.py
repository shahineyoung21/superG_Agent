import os
import ccxt
import pandas as pd
import google.generativeai as genai

# تهيئة الذكاء الاصطناعي
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-pro')

def get_crypto_data(symbol="BTC/USDT"):
    exchange = ccxt.binance({'enableRateLimit': True})
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=50)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df.iloc[-1]

def run_agent_analysis():
    last_data = get_crypto_data()
    
    prompt = f"""
    أنت AI Agent متخصص في التداول وتحليل المخاطر.
    بيانات السوق الحالية لـ BTC/USDT:
    - السعر الحالي: {last_data['close']}
    - مؤشر RSI: {last_data['RSI']:.2f}

    قم بتقديم:
    1. تحليل سريع للوضع الحالي.
    2. قرار التداول (شراء / بيع / انتظار) مع تحديد نسبة المخاطرة.
    3. توصية لتطوير الاستراتيجية للعملية القادمة.
    """
    
    response = model.generate_content(prompt)
    print("--- تقرير الـ Agent ---")
    print(response.text)
    
    with open("agent_log.txt", "a", encoding="utf-8") as f:
        f.write(f"\n--- Analysis for {last_data['close']} ---\n" + response.text + "\n")

if __name__ == "__main__":
    run_agent_analysis()
  
