FROM supabase/gotrue:v2.132.3

# Switch to root to install psql client and fix migration
USER root
RUN apk add --no-cache postgresql-client

# Copy scripts
COPY init-auth-schema.sql /tmp/init-auth-schema.sql
COPY auth-wrapper.sh /usr/local/bin/auth-wrapper.sh
COPY fix-migration.sql /tmp/fix-migration.sql
RUN chmod +x /usr/local/bin/auth-wrapper.sh

# Fix the problematic migration file directly
RUN if [ -f "/usr/local/etc/auth/migrations/20221208132122_backfill_email_last_sign_in_at.up.sql" ]; then \
      cp /tmp/fix-migration.sql /usr/local/etc/auth/migrations/20221208132122_backfill_email_last_sign_in_at.up.sql; \
    fi

# Switch back to the original user
USER 65532

# Override the entrypoint to use our wrapper
ENTRYPOINT ["/usr/local/bin/auth-wrapper.sh"]

# Security: Run as non-root user
USER 1001
