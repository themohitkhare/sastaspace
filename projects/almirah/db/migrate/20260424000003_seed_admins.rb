# frozen_string_literal: true

# Data migration: ensure the owner email is present in public.admins
# (the legacy allowlist table) AND that public.users.admin is in sync
# for any already-registered user whose email appears there.
#
# public.admins pre-exists from db/migrations/0004_admins_and_helpers.sql
# and is shared with the legacy stack. Idempotent: ON CONFLICT DO NOTHING
# on the insert, UPDATE only flips false → true.
class SeedAdmins < ActiveRecord::Migration[8.1]
  ADMIN_EMAIL = "mohitkhare582@gmail.com"

  def up
    # Guard: public.admins must already exist (created by 0004_admins_and_helpers.sql).
    regclass = select_value("SELECT to_regclass('public.admins')")
    if regclass.nil?
      raise "public.admins does not exist — run db/migrations/0004_admins_and_helpers.sql first"
    end

    execute <<~SQL
      INSERT INTO public.admins (email, note)
      VALUES ('#{ADMIN_EMAIL}', 'owner')
      ON CONFLICT (email) DO NOTHING;
    SQL

    # Backfill users.admin for anyone already registered whose email is in
    # public.admins. No-op on a fresh DB; corrective on subsequent runs.
    execute <<~SQL
      UPDATE public.users u
         SET admin      = true,
             updated_at = now()
       WHERE u.email_address IN (SELECT email FROM public.admins)
         AND u.admin = false;
    SQL
  end

  def down
    # Intentionally do NOT delete from public.admins — that table is shared
    # with the legacy GoTrue stack and removal could lock out the old admin UI.
    execute <<~SQL
      UPDATE public.users
         SET admin      = false,
             updated_at = now()
       WHERE email_address = '#{ADMIN_EMAIL}';
    SQL
  end
end
