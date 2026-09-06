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