-- CI fix: ensure pgcrypto + lock PUBLIC schema (Dependabot PR)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
