import json
import base64
import re
from datetime import datetime, timezone
from io import BytesIO

from app.config import settings
from app.models import ReceiptDraft

PROMPT = '''Распознай данные с фотографии кассового чека. Верни только JSON без markdown:
{"date":"YYYY-MM-DD","total":1234.56,"items":[{"name":"товар","price":123.45,"category":"Продукты"}]}
Категория каждого товара должна быть одной из: Продукты, Коммунальные услуги, Транспорт, Кафе и рестораны, Здоровье, Дом, Развлечения, Подписки, Образование, Другое. Если поле не видно, используй пустую строку или 0. Не добавляй пояснений.'''


def parse_scanner_response(content: str) -> dict:
    text = content.strip().replace('```json', '').replace('```', '').strip()
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise ValueError('GigaChat вернул некорректный JSON')
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError('GigaChat вернул некорректный JSON') from exc
    if not isinstance(data, dict):
        raise ValueError('Некорректный формат чека')
    return data


def _number(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float(re.sub(r'[^0-9.,-]', '', str(value)).replace(',', '.') or 0)


def scan_receipt_image(content: bytes, filename: str, content_type: str) -> ReceiptDraft:
    if not settings.deepseek_api_key:
        raise RuntimeError('Сканер чеков не настроен: добавьте DEEPSEEK_API_KEY в .env')
    from openai import OpenAI
    client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
    image_url = f'data:{content_type};base64,{base64.b64encode(content).decode()}'
    result = client.chat.completions.create(model='deepseek-v4-flash-vision-exp', temperature=0.05,
        response_format={'type': 'json_object'}, messages=[{'role': 'user', 'content': [
            {'type': 'text', 'text': PROMPT}, {'type': 'image_url', 'image_url': {'url': image_url}}
        ]}])
    data = parse_scanner_response(result.choices[0].message.content or '')
    date_raw = str(data.get('date') or '')
    try:
        purchased_at = datetime.fromisoformat(date_raw).replace(tzinfo=timezone.utc) if date_raw else datetime.now(timezone.utc)
    except ValueError:
        purchased_at = datetime.now(timezone.utc)
    items = []
    for item in data.get('items') or []:
        if isinstance(item, dict):
            items.append({'name': str(item.get('name') or 'Товар'), 'price': _number(item.get('price', 0)), 'category': str(item.get('category') or 'Другое')})
    return ReceiptDraft(merchant=str(data.get('shop') or 'Чек'), amount=_number(data.get('total', 0)), purchased_at=purchased_at,
                        category=(items[0]['category'] if items else 'Другое'),
                        fiscal_fields={'date': date_raw, 'total': str(data.get('total', ''))}, items=items, provider='gigachat')
