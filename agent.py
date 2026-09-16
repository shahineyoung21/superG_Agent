import requests
import json

def generate_with_fallback_stream(prompt):
    last_error = None
    for model_name in MODEL_CANDIDATES:
        try:
            print(f"Trying OpenRouter model: {model_name} (streaming)...")
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True
                },
                stream=True
            )

            # لو حصل خطأ قبل بدء الـ stream (مثل موديل غير متاح)
            if response.status_code != 200:
                error_data = response.json()
                raise RuntimeError(error_data['error']['message'])

            full_text = ""
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith(': OPENROUTER PROCESSING'):
                        continue  # تعليقات لمنع timeout، يتم تجاهلها
                    if line_text.startswith('data: '):
                        data = line_text[6:]
                        if data == '[DONE]':
                            break
                        try:
                            parsed = json.loads(data)
                            if 'error' in parsed:
                                raise RuntimeError(parsed['error']['message'])
                            content = parsed['choices'][0]['delta'].get('content')
                            if content:
                                print(content, end='', flush=True)
                                full_text += content
                        except json.JSONDecodeError:
                            continue

            print()  # سطر جديد بعد انتهاء الستريم
            return full_text

        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            last_error = e
            continue

    raise RuntimeError(f"Could not generate content with any OpenRouter model! Last error: {last_error}")