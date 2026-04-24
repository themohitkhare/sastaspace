# frozen_string_literal: true

# Creates public.users — the shared identity table for all Rails apps.
# Designed to co-exist with the existing supabase/postgres instance where
# public.admins (email PK) already exists and is used by the legacy stack.
#
# Idempotency: uses `create_table if_not_exists: true` and IF NOT EXISTS
# guards so this migration is safe to replay on a DB that partially ran it.
class CreateUsers < ActiveRecord::Migration[8.0]
  def up
    # public.users is the canonical identity store for the Rails stack.
    # google_uid is nullable to allow email/password registrations that never
    # go through Google OAuth — e.g. future local-dev accounts.
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS public.users (
        id         BIGSERIAL PRIMARY KEY,
        email      TEXT      NOT NULL,
        name       TEXT,
        google_uid TEXT,
        avatar_url TEXT,
        admin      BOOLEAN   NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );

      CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
        ON public.users (email);

      CREATE INDEX IF NOT EXISTS idx_users_google_uid
        ON public.users (google_uid)
        WHERE google_uid IS NOT NULL;
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS public.users;"
  end
end
