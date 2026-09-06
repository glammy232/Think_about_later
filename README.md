# Круг — backend MVP

Backend для сервиса совместного учета расходов семьи или группы друзей. Сейчас данные хранятся в памяти и автоматически сбрасываются после перезапуска. Это сделано намеренно: слой хранения изолирован, чтобы позже подключить базу данных без изменения API для frontend.

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Открыть:

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Проверка сервера: http://localhost:8000/api/health

Также можно запустить через Docker:

```bash
docker compose up --build
```

## Демо-данные

- Группа: `group-1` — «Квартира на Ленина».
- Текущий пользователь по умолчанию: `user-1` — Алексей.
- Участники: `user-1` ... `user-5`.
- В заголовке запросов можно передать `X-User-Id`.

## Что поддерживает API

- главная сводка — `GET /api/groups/{group_id}/dashboard`;
- участники группы;
- добавление новых участников в группу;
- расходы и доходы, равное и ручное деление;
- деление по процентам с автоматическим расчетом сумм;
- предложенные категории и произвольные категории пользователя;
- автоматический расчет балансов и минимальных переводов;
- прямые долги и их погашение;
- фиксация переводов между участниками с автоматическим обновлением баланса;
- аналитика по категориям, месяцам и участникам;
- разбор QR-строки чека в черновик расхода;
- AI-помощник DeepSeek: анализ финансов и создание операций через подтверждаемые черновики;
- настройки имени, фотографии и валюты пользователя;
- изменение названия общей группы;
- CORS для локального frontend.

Полный контракт и примеры запросов доступны в Swagger.

## Подключение frontend

Базовый URL в разработке:

```text
http://localhost:8000/api
```

Пример:

```js
const response = await fetch('http://localhost:8000/api/groups/group-1/dashboard', {
  headers: { 'X-User-Id': 'user-1' }
});
const dashboard = await response.json();
```

Для создания расхода:

```js
await fetch('http://localhost:8000/api/groups/group-1/operations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'expense',
    title: 'Продукты',
    amount: 1500,
    category: 'Продукты',
    payer_id: 'user-1',
    participant_ids: ['user-1', 'user-2', 'user-3'],
    split_type: 'equal'
  })
});
```

## Кнопки интерфейса и endpoints

| Элемент | Endpoint |
|---|---|
| Главная | `GET /groups/{id}/dashboard` |
| Операции | `GET /groups/{id}/operations` |
| Категории | `GET /groups/{id}/categories` |
| Балансы | `GET /groups/{id}/balances` |
| Аналитика | `GET /groups/{id}/analytics` |
| Задолженности | `GET /groups/{id}/debts` |
| Участники | `GET /groups/{id}/members` |
| Добавить участника | `POST /groups/{id}/members` |
| Расход | `POST /groups/{id}/operations`, `type=expense` |
| Доход | `POST /groups/{id}/operations`, `type=income` |
| Долг | `POST /groups/{id}/debts` |
| Погасить рассчитанный долг | `POST /groups/{id}/payments` |
| Чек | `POST /receipts/parse`, затем создание операции |
| AI-помощник | `POST /groups/{id}/assistant` |
| Настройки | `GET/PATCH /users/{id}/settings` |
| Название группы | `PATCH /groups/{id}/settings` |

Во frontend к указанным путям нужно добавлять префикс `/api`.

### Неравное распределение расхода

Если первый пользователь заплатил 5 000 ₽, а второй должен 3 000 ₽ и третий 2 000 ₽, frontend отправляет:

```json
{
  "type": "expense",
  "title": "Продукты на троих",
  "amount": 5000,
  "category": "Продукты",
  "payer_id": "user-1",
  "participant_ids": ["user-2", "user-3"],
  "split_type": "custom",
  "shares": [
    { "user_id": "user-2", "amount": 3000 },
    { "user_id": "user-3", "amount": 2000 }
  ]
}
```

Сумма всех `shares` обязана совпадать с `amount`. После создания операции главная сводка, список операций, балансы, задолженности и аналитика пересчитываются автоматически.

Для распределения по процентам используется `split_type: "percentage"`:

```json
{
  "type": "expense",
  "title": "Аренда",
  "amount": 10000,
  "category": "Дом",
  "payer_id": "user-1",
  "participant_ids": ["user-1", "user-2", "user-3"],
  "split_type": "percentage",
  "shares": [
    { "user_id": "user-1", "percentage": 20 },
    { "user_id": "user-2", "percentage": 30 },
    { "user_id": "user-3", "percentage": 50 }
  ]
}
```

Проценты должны давать ровно 100%. В ответе на любой расход каждая доля содержит и сумму, и рассчитанный процент. Поле `category` принимает как предложенное, так и любое собственное название. Предложенные и уже использованные собственные категории возвращает `GET /api/groups/{group_id}/categories`.

Дополнительные правила API:

- один участник не может повторяться в `participant_ids` или `shares`;
- платеж не может превышать текущую рассчитанную задолженность;
- поддерживаются валюты `RUB`, `USD` и `EUR`;
- фотография профиля должна быть корректным HTTP(S)-адресом;
- имена и названия очищаются от пробелов и не могут быть пустыми.

## Будущая интеграция базы данных

Контракт хранилища находится в `app/storage.py` (`Storage`). Специалист по БД реализует класс `DatabaseStorage` с теми же методами, после чего достаточно заменить объект `storage`. Роуты и JSON-контракт менять не потребуется.

## AI-интеграция

Адаптированный системный prompt находится в `ai/finance_assistant_prompt.txt`, строгие JSON-схемы инструментов — в `ai/tools.json`, а согласованный backend-контракт — в `ai/AI_TOOLS_BACKEND_TZ.txt`. `app/ai_config.py` загружает эти файлы и безопасно подставляет текущую группу, пользователя, участников, категории, дату и валюту.

AI не имеет доступа к БД и не получает произвольный `group_id` в параметрах tools. Он обращается к Python-backend, а backend проверяет доступ, получает точные данные из Storage и выполняет все финансовые расчёты. Расходы, доходы и долги создаются в два шага: подготовка черновика и отдельное подтверждение пользователя.

Для запуска создайте `.env` из `.env.example` и задайте `DEEPSEEK_API_KEY`. Frontend отправляет сообщение в `POST /api/groups/{group_id}/assistant` и сохраняет возвращённый `conversation_id` для следующих сообщений диалога. Поле `pending_action` содержит черновик. Подтвердить или отменить его можно следующим сообщением в том же диалоге либо явно через:

- `POST /api/groups/{group_id}/assistant/actions/{action_id}/confirm`;
- `POST /api/groups/{group_id}/assistant/actions/{action_id}/cancel`.

Повторное подтверждение безопасно и не создаёт дубль. Черновик привязан к группе и текущему пользователю из заголовка `X-User-Id`.

## Тесты

```bash
python -m pytest -q
ruff check app tests
ruff format --check app tests
```
