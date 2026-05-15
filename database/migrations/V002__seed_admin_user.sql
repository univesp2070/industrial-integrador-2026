INSERT INTO users (id, email, password_hash, name, role, active)
VALUES (
    gen_random_uuid(),
    'admin@edgeai.local',
    '$2a$10$fKzFJz4TgUOyWxwUvz5LA.J9QAk5jfEdJ.1x5Yre5AG.9sJ6COsUu',
    'Admin',
    'admin',
    true
)
ON CONFLICT (email) DO NOTHING;
