# frozen_string_literal: true

# Data migration: seed the owner email into public.admins (the legacy
# allowlist table shared with the old GoTrue stack). Admin-ness in the
# Rails app is determined at query time by joining User.email_address
# against public.admins.email — no admin boolean on users.
#
# public.admins pre-exists from db/migrations/0004_admins_and_helpers.sql.
# Idempotent via ON CONFLICT DO NOTHING.
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
  end

  def down
    # Intentionally do NOT delete from public.admins — that table is still
    # referenced by the legacy GoTrue stack during the transition window.
  end
end
