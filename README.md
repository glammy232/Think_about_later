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
- автоматический расчет балансов и минимальных переводов;
- прямые долги и их погашение;
- фиксация переводов между участниками с автоматическим обновлением баланса;
- аналитика по категориям, месяцам и участникам;
- разбор QR-строки чека в черновик расхода;
- временный mock AI-помощника;
- настройки валюты пользователя;
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

## Будущая интеграция базы данных

Контракт хранилища находится в `app/storage.py` (`Storage`). Специалист по БД реализует класс `DatabaseStorage` с теми же методами, после чего достаточно заменить объект `storage`. Роуты и JSON-контракт менять не потребуется.

## Тесты

```bash
pytest -q
```
