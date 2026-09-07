CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,

    group_id INTEGER NOT NULL
        REFERENCES groups(id)
        ON DELETE RESTRICT,

    paid_by INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE RESTRICT,

    category_id INTEGER NOT NULL
        REFERENCES categories(id)
        ON DELETE RESTRICT,

    amount NUMERIC(10,2) NOT NULL
        CHECK (amount > 0),

    description TEXT,

    expense_date TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ DEFAULT now()
);