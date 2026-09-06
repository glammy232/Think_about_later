CREATE TABLE settlements (
    id SERIAL PRIMARY KEY,

    group_id INTEGER NOT NULL
        REFERENCES groups(id)
        ON DELETE CASCADE,

    from_user_id INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE RESTRICT,

    to_user_id INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE RESTRICT,

    amount NUMERIC(10,2) NOT NULL
        CHECK (amount > 0),

    settled_at TIMESTAMPTZ DEFAULT now(),

    created_at TIMESTAMPTZ DEFAULT now(),

    CHECK (from_user_id <> to_user_id)
);