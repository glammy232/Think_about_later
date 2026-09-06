-- =========================================================
-- SEED-ДАННЫЕ ДЛЯ MVP
-- =========================================================

-- -------------------------
-- 1. Пользователи
-- -------------------------

INSERT INTO users (
    id,
    name,
    email,
    password_hash
)
VALUES
    (1, 'Алексей', 'alexey@example.com', 'test_hash_alexey'),
    (2, 'Мария', 'maria@example.com', 'test_hash_maria'),
    (3, 'Иван', 'ivan@example.com', 'test_hash_ivan'),
    (4, 'Анна', 'anna@example.com', 'test_hash_anna'),
    (5, 'Дмитрий', 'dmitry@example.com', 'test_hash_dmitry');

-- -------------------------
-- 2. Группа
-- -------------------------

INSERT INTO groups (
    id,
    name
)
VALUES
    (1, 'Квартира на Ленина');

-- -------------------------
-- 3. Участники группы
-- -------------------------

INSERT INTO group_members (
    group_id,
    user_id,
    role
)
VALUES
    (1, 1, 'admin'),
    (1, 2, 'member'),
    (1, 3, 'member'),
    (1, 4, 'member'),
    (1, 5, 'member');

-- -------------------------
-- 4. Категории расходов
-- -------------------------

INSERT INTO categories (
    id,
    name
)
VALUES
    (1, 'Продукты'),
    (2, 'Коммунальные услуги'),
    (3, 'Интернет'),
    (4, 'Бытовые товары'),
    (5, 'Развлечения'),
    (6, 'Транспорт');

-- -------------------------
-- 5. Расходы
--
-- Дмитрий (user_id = 5)
-- намеренно не оплатил
-- ни одного расхода
-- -------------------------

INSERT INTO expenses (
    id,
    group_id,
    category_id,
    paid_by,
    amount,
    description,
    expense_date
)
VALUES
    (1, 1, 1, 1, 3200.00, 'Продукты на неделю', now() - INTERVAL '58 days'),
    (2, 1, 2, 2, 5400.00, 'Коммунальные услуги', now() - INTERVAL '54 days'),
    (3, 1, 3, 3, 900.00, 'Интернет', now() - INTERVAL '50 days'),
    (4, 1, 4, 4, 1850.00, 'Бытовая химия', now() - INTERVAL '45 days'),
    (5, 1, 1, 1, 2750.00, 'Продукты', now() - INTERVAL '41 days'),
    (6, 1, 5, 2, 4200.00, 'Поход в кино', now() - INTERVAL '37 days'),
    (7, 1, 6, 3, 1500.00, 'Такси', now() - INTERVAL '32 days'),
    (8, 1, 2, 4, 6100.00, 'Коммунальные услуги', now() - INTERVAL '28 days'),
    (9, 1, 1, 1, 3400.00, 'Продукты', now() - INTERVAL '23 days'),
    (10, 1, 4, 2, 2100.00, 'Средства для дома', now() - INTERVAL '18 days'),
    (11, 1, 5, 3, 3600.00, 'Совместный ужин', now() - INTERVAL '12 days'),
    (12, 1, 1, 4, 2900.00, 'Продукты', now() - INTERVAL '8 days'),
    (13, 1, 3, 1, 900.00, 'Интернет', now() - INTERVAL '5 days'),
    (14, 1, 6, 2, 1200.00, 'Поездка по городу', now() - INTERVAL '3 days'),
    (15, 1, 1, 3, 4100.00, 'Большая закупка продуктов', now() - INTERVAL '1 day');

-- -------------------------
-- 6. Доли участников расходов
-- -------------------------

-- Расход 1: 3200 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (1, 1, 800.00),
    (1, 2, 800.00),
    (1, 3, 800.00),
    (1, 4, 400.00),
    (1, 5, 400.00);

-- Расход 2: 5400 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (2, 1, 1350.00),
    (2, 2, 1350.00),
    (2, 3, 1350.00),
    (2, 4, 1350.00);

-- Расход 3: 900 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (3, 1, 225.00),
    (3, 2, 225.00),
    (3, 3, 225.00),
    (3, 4, 225.00);

-- Расход 4: 1850 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (4, 1, 500.00),
    (4, 2, 500.00),
    (4, 3, 500.00),
    (4, 4, 350.00);

-- Расход 5: 2750 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (5, 1, 750.00),
    (5, 2, 700.00),
    (5, 3, 700.00),
    (5, 4, 600.00);

-- Расход 6: 4200 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (6, 1, 1200.00),
    (6, 2, 1000.00),
    (6, 3, 1000.00),
    (6, 4, 1000.00);

-- Расход 7: 1500 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (7, 1, 500.00),
    (7, 2, 500.00),
    (7, 3, 500.00);

-- Расход 8: 6100 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (8, 1, 1600.00),
    (8, 2, 1500.00),
    (8, 3, 1500.00),
    (8, 4, 1500.00);

-- Расход 9: 3400 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (9, 1, 1000.00),
    (9, 2, 800.00),
    (9, 3, 800.00),
    (9, 4, 800.00);

-- Расход 10: 2100 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (10, 1, 600.00),
    (10, 2, 500.00),
    (10, 3, 500.00),
    (10, 4, 500.00);

-- Расход 11: 3600 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (11, 1, 900.00),
    (11, 2, 900.00),
    (11, 3, 900.00),
    (11, 4, 900.00);

-- Расход 12: 2900 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (12, 1, 800.00),
    (12, 2, 700.00),
    (12, 3, 700.00),
    (12, 4, 700.00);

-- Расход 13: 900 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (13, 1, 300.00),
    (13, 2, 300.00),
    (13, 3, 300.00);

-- Расход 14: 1200 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (14, 1, 400.00),
    (14, 2, 400.00),
    (14, 3, 400.00);

-- Расход 15: 4100 рублей
INSERT INTO expense_participants (expense_id, user_id, share) VALUES
    (15, 1, 1100.00),
    (15, 2, 1000.00),
    (15, 3, 1000.00),
    (15, 4, 1000.00);

-- -------------------------
-- 7. Частичные погашения долгов
-- -------------------------

INSERT INTO settlements (
    group_id,
    from_user_id,
    to_user_id,
    amount,
    settled_at
)
VALUES
    (1, 2, 1, 500.00, now() - INTERVAL '10 days'),
    (1, 4, 2, 750.00, now() - INTERVAL '4 days');

-- -------------------------
-- 8. Обновление SERIAL-последовательностей
-- -------------------------

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('groups_id_seq', (SELECT MAX(id) FROM groups));
SELECT setval('categories_id_seq', (SELECT MAX(id) FROM categories));
SELECT setval('expenses_id_seq', (SELECT MAX(id) FROM expenses));