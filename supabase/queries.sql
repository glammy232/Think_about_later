-- =========================================
-- Список расходов группы (с пагинацией)
-- Параметры: group_id, limit, offset
-- =========================================
-- Перед повторным запуском файла в той же сессии psql:
-- DEALLOCATE group_expenses;
PREPARE group_expenses (int, int, int) AS
SELECT
    e.expense_date,
    e.amount,
    e.description,
    c.name AS category_name,
    u.name AS paid_by_name
FROM expenses e
JOIN categories c ON c.id = e.category_id
JOIN users u ON u.id = e.paid_by
WHERE e.group_id = $1
ORDER BY e.expense_date DESC
LIMIT $2 OFFSET $3;

EXECUTE group_expenses(1, 10, 0);


-- =========================================
-- Баланс каждого участника группы
-- Параметр: group_id
-- Fan-out избегаем через отдельные CTE на каждую сумму
-- =========================================
-- Перед повторным запуском файла в той же сессии psql:
-- DEALLOCATE group_balances;
PREPARE group_balances (int) AS
WITH paid AS (
    -- сколько каждый заплатил за расходы группы
    SELECT paid_by AS user_id, SUM(amount) AS total_paid
    FROM expenses
    WHERE group_id = $1
    GROUP BY paid_by
),
owed AS (
    -- сколько на каждого приходится доли в расходах группы
    SELECT ep.user_id, SUM(ep.share) AS total_owed
    FROM expense_participants ep
    JOIN expenses e ON e.id = ep.expense_id
    WHERE e.group_id = $1
    GROUP BY ep.user_id
),
settled_out AS (
    -- сколько каждый отдал по факту (settlements)
    SELECT from_user_id AS user_id, SUM(amount) AS total_settled_out
    FROM settlements
    WHERE group_id = $1
    GROUP BY from_user_id
),
settled_in AS (
    -- сколько каждый получил по факту (settlements)
    SELECT to_user_id AS user_id, SUM(amount) AS total_settled_in
    FROM settlements
    WHERE group_id = $1
    GROUP BY to_user_id
)
SELECT
    u.name,
    COALESCE(p.total_paid, 0)
    - COALESCE(o.total_owed, 0)
    + COALESCE(so.total_settled_out, 0)
    - COALESCE(si.total_settled_in, 0) AS balance
FROM users u
LEFT JOIN paid p         ON p.user_id  = u.id
LEFT JOIN owed o         ON o.user_id  = u.id
LEFT JOIN settled_out so ON so.user_id = u.id
LEFT JOIN settled_in si  ON si.user_id = u.id
WHERE u.id IN (SELECT user_id FROM group_members WHERE group_id = $1)
ORDER BY u.name;


EXECUTE group_balances(1);
-- =========================================
-- Попарные задолженности участников группы
-- Параметр: group_id
--
-- Положительный balance = участнику должны
-- Отрицательный balance = участник должен
--
-- Без оптимизации количества переводов.
-- Должники и кредиторы сопоставляются
-- по убыванию абсолютной суммы.
-- =========================================

-- Перед повторным запуском файла в той же сессии psql:
-- DEALLOCATE group_debts;

PREPARE group_debts (int) AS

WITH paid AS (

    SELECT
        paid_by AS user_id,
        SUM(amount) AS total_paid
    FROM expenses
    WHERE group_id = $1
    GROUP BY paid_by

),

owed AS (

    SELECT
        ep.user_id,
        SUM(ep.share) AS total_owed
    FROM expense_participants ep
    JOIN expenses e ON e.id = ep.expense_id
    WHERE e.group_id = $1
    GROUP BY ep.user_id

),

settled_out AS (

    SELECT
        from_user_id AS user_id,
        SUM(amount) AS total_settled_out
    FROM settlements
    WHERE group_id = $1
    GROUP BY from_user_id

),

settled_in AS (

    SELECT
        to_user_id AS user_id,
        SUM(amount) AS total_settled_in
    FROM settlements
    WHERE group_id = $1
    GROUP BY to_user_id

),

group_balances AS (

    SELECT
        u.id AS user_id,
        u.name,
        COALESCE(p.total_paid, 0)
        - COALESCE(o.total_owed, 0)
        + COALESCE(so.total_settled_out, 0)
        - COALESCE(si.total_settled_in, 0) AS balance

    FROM users u

    LEFT JOIN paid p
        ON p.user_id = u.id

    LEFT JOIN owed o
        ON o.user_id = u.id

    LEFT JOIN settled_out so
        ON so.user_id = u.id

    LEFT JOIN settled_in si
        ON si.user_id = u.id

    WHERE u.id IN (
        SELECT user_id
        FROM group_members
        WHERE group_id = $1
    )

),

debtors AS (

    SELECT
        user_id,
        name,
        -balance AS amount,

        COALESCE(
            SUM(-balance) OVER (
                ORDER BY -balance DESC, user_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ),
            0
        ) AS range_start

    FROM group_balances
    WHERE balance < 0

),

creditors AS (

    SELECT
        user_id,
        name,
        balance AS amount,

        COALESCE(
            SUM(balance) OVER (
                ORDER BY balance DESC, user_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ),
            0
        ) AS range_start

    FROM group_balances
    WHERE balance > 0

),

debtor_ranges AS (

    SELECT
        user_id,
        name,
        amount,
        range_start,
        range_start + amount AS range_end
    FROM debtors

),

creditor_ranges AS (

    SELECT
        user_id,
        name,
        amount,
        range_start,
        range_start + amount AS range_end
    FROM creditors

)

SELECT
    d.name AS debtor_name,
    c.name AS creditor_name,

    LEAST(d.range_end, c.range_end)
    - GREATEST(d.range_start, c.range_start) AS amount

FROM debtor_ranges d

JOIN creditor_ranges c
    ON d.range_start < c.range_end
   AND c.range_start < d.range_end

WHERE LEAST(d.range_end, c.range_end)
    - GREATEST(d.range_start, c.range_start) > 0

ORDER BY
    amount DESC,
    debtor_name,
    creditor_name;

EXECUTE group_debts(1);