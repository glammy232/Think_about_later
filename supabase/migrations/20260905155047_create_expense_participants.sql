CREATE TABLE expense_participants (
    id SERIAL PRIMARY KEY,

    expense_id INTEGER NOT NULL
        REFERENCES expenses(id)
        ON DELETE CASCADE,

    user_id INTEGER NOT NULL
        REFERENCES users(id),

    share NUMERIC(10,2) NOT NULL
        CHECK (share >= 0),

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (expense_id, user_id)
);