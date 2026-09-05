CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON COLUMN users.id IS
    'Уникальный идентификатор пользователя';

COMMENT ON COLUMN users.name IS
    'Имя пользователя';

COMMENT ON COLUMN users.email IS
    'Электронная почта пользователя';

COMMENT ON COLUMN users.password_hash IS
    'Хеш пароля пользователя';

COMMENT ON COLUMN users.created_at IS
    'Дата и время создания записи';