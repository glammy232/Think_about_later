CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    group_id INTEGER NOT NULL REFERENCES groups(id),
    
    role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
    
    joined_at TIMESTAMPTZ DEFAULT now(),
    
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE (user_id, group_id)
);