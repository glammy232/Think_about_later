-- Fields and entities required by the FastAPI contract.
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS split_type TEXT NOT NULL DEFAULT 'equal'
    CHECK (split_type IN ('equal', 'custom', 'percentage'));
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS comment TEXT;
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual';

CREATE TABLE IF NOT EXISTS incomes (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    received_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    income_date DATE NOT NULL,
    comment TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS direct_debts (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    debtor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    creditor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'settled')),
    due_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    settled_at TIMESTAMPTZ,
    CHECK (debtor_id <> creditor_id)
);

ALTER TABLE settlements ADD COLUMN IF NOT EXISTS comment TEXT;

CREATE INDEX IF NOT EXISTS idx_incomes_group_date
    ON incomes(group_id, income_date DESC);
CREATE INDEX IF NOT EXISTS idx_direct_debts_group_status
    ON direct_debts(group_id, status);
