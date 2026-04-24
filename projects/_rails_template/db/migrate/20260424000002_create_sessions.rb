# frozen_string_literal: true

# Creates public.sessions — Rails-native session store.
# The session cookie carries only sessions.id (UUID).  All session state
# lives server-side here, avoiding encrypted-cookie bloat and enabling
# instant invalidation per device.
#
# Indexed for:
#   - lookup by id (primary key — cookie read on every request)
#   - cleanup by user_id (delete all sessions when a user is deactivated)
#   - expiry sweeps by last_active_at (pg_cron job: DELETE WHERE last_active_at < now() - interval '30 days')
class CreateSessions < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS public.sessions (
        id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id        BIGINT      NOT NULL
                         REFERENCES public.users (id) ON DELETE CASCADE,
        user_agent     TEXT,
        ip_address     INET,
        last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
      );

      CREATE INDEX IF NOT EXISTS idx_sessions_user_id
        ON public.sessions (user_id);

      CREATE INDEX IF NOT EXISTS idx_sessions_last_active_at
        ON public.sessions (last_active_at DESC);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS public.sessions;"
  end
end
