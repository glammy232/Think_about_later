# Family Budget — Database Module

Модуль базы данных для приложения ведения группового семейного бюджета: пользователи, группы, расходы, распределение долей и расчёт долгов.

Ответственный за модуль: **Казаковцев Марк**
Ветка: `feature/database`

---

## Стек

- **СУБД:** PostgreSQL
- Типы id: `SERIAL`
- Даты: `TIMESTAMPTZ`
- Деньги: `NUMERIC(10,2)` (никогда `FLOAT`)
- Именование: таблицы во множественном числе, поля в `snake_case`

---

## Структура таблиц

| Таблица | Назначение |
|---|---|
| `users` | пользователи (id, имя, email, пароль-хэш, дата регистрации) |
| `groups` | группы/семьи (id, название, кто создал) |
| `group_members` | связь users↔groups (роль: admin/member) |
| `categories` | глобальный справочник категорий расходов |
| `expenses` | расходы (группа, плательщик, категория, сумма, дата) |
| `expense_participants` | участники конкретного расхода и их доли |

### Связи (ER)

```
users ──1:M── group_members ──M:1── groups
groups ──1:M── expenses
expenses ──1:M── expense_participants ──M:1── users
users ──1:M── groups            (created_by)
expenses ──M:1── users           (paid_by)
expenses ──M:1── categories
```

### Ключевые решения

- **Категории общие для всех групп** (не привязаны к `group_id`) — упрощает справочник и аналитику по категориям.
- **Долги (`debts`) не хранятся отдельной таблицей** — вычисляются запросом на лету от `expenses` + `expense_participants`. Меньше риска рассинхрона данных.
- **Доли участников (`share`) хранятся в валюте**, не в процентах — точнее при неровном делении суммы.
- Все внешние ключи имеют явно заданное поведение `ON DELETE` (см. комментарии в `schema.sql`).

---

## Структура репозитория (модуль БД)

```
/db
 ├── migrations/
 │    ├── 001_create_users.sql
 │    ├── 002_create_groups.sql
 │    ├── 003_create_group_members.sql
 │    ├── 004_create_categories.sql
 │    ├── 005_create_expenses.sql
 │    └── 006_create_expense_participants.sql
 ├── seeds/
 │    └── seed.sql              — тестовые данные (включая edge cases)
 └── queries.sql                — все рабочие запросы + sanity-check запросы, в одном файле
```

Каждый файл миграции = ровно один коммит (`feat(db): create users table` → `001_create_users.sql`). Применённые по порядку миграции и есть твоя схема — отдельный `schema.sql` не нужен.

---

## Как поднять локально

```bash
# создать БД
createdb family_budget

# накатить миграции по порядку
psql -d family_budget -f db/migrations/001_create_users.sql
psql -d family_budget -f db/migrations/002_create_groups.sql
psql -d family_budget -f db/migrations/003_create_group_members.sql
psql -d family_budget -f db/migrations/004_create_categories.sql
psql -d family_budget -f db/migrations/005_create_expenses.sql
psql -d family_budget -f db/migrations/006_create_expense_participants.sql

# наполнить тестовыми данными
psql -d family_budget -f db/seeds/seed.sql
```

---

## Готовые запросы (`queries.sql`)

Один файл, блоки разделены комментариями — Диме достаточно Ctrl+F по названию:

```sql
-- === Список расходов ===
-- === Балансы участников ===
-- === Задолженности ===
-- === Аналитика (по категориям, по месяцам) ===
-- === Sanity-check: сумма долей = сумме расхода ===
-- === Sanity-check: сумма балансов группы = 0 ===
```

Ключевые sanity-check запросы прогонять перед демо / после значимых изменений схемы:
- сумма долей (`share`) по расходу должна совпадать с суммой расхода (`amount`);
- сумма всех балансов внутри группы должна быть равна нулю (иначе ошибка в расчёте долгов).

---

## Соглашения по коммитам

Формат: `feat(db): <что сделано>`

```
feat(db): create users table
feat(db): create groups table
feat(db): create group_members table
feat(db): create categories table
feat(db): create expenses table
feat(db): create expense_participants table
feat(db): add seed data with edge cases
feat(db): add queries (list, balance, debts, analytics)
```

Коммит и `push origin feature/database` — после каждой готовой миграции / после наполнения сидами / после блока запросов. Не пачками.

---

## Для бэкенд-интеграции (Дима)

- Схема — все файлы в `db/migrations/`, применённые по порядку.
- Примеры вызовов и ожидаемый формат ответа — в комментариях прямо над каждым блоком в `queries.sql`.
- Если нужен другой формат данных (например, JSON-агрегация вместо плоских строк) — дай знать, доработаем запросы под конкретный формат ответа API.

---

## Возможное развитие (если останется время)

- **Упрощение долгов** — алгоритм минимизации количества переводов между участниками группы (аналог Splitwise), поверх запроса `debts.sql`.
- Повторяющиеся платежи (`recurring_expenses`).
- Лимиты бюджета по категориям (`budgets`).
