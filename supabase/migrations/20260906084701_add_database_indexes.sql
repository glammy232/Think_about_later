-- Аналитика расходов по категориям внутри конкретной группы
CREATE INDEX idx_expenses_group_category
ON expenses (group_id, category_id);

-- Быстрый поиск участников конкретного расхода
CREATE INDEX idx_expense_participants_expense_id
ON expense_participants (expense_id);

-- Быстрый поиск settlements внутри конкретной группы
CREATE INDEX idx_settlements_group_id
ON settlements (group_id);

-- Быстрый поиск переводов, отправленных пользователем
CREATE INDEX idx_settlements_from_user_id
ON settlements (from_user_id);

-- Быстрый поиск переводов, полученных пользователем
CREATE INDEX idx_settlements_to_user_id
ON settlements (to_user_id);