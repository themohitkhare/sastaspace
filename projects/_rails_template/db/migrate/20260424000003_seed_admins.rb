# frozen_string_literal: true

# Data migration: ensure the admin email is present in both tables.
#
# 1. public.admins (legacy, email-PK table created by db/migrations/0004_admins_and_helpers.sql)
#    — insert owner row with ON CONFLICT DO NOTHING so it's safe if already present.
#
# 2. public.users.admin flag — backfill any users whose email appears in
#    public.admins with admin = true.  Runs as a bulk UPDATE, which is a no-op
#    if the users table is empty or already correct.
#
# This migration is intentionally reversible: down() clears the admin flag
# on the test email but does NOT delete from public.admins (that table is
# owned by the legacy sql migrations, not this app).
class SeedAdmins < ActiveRecord::Migration[8.0]
  ADMIN_EMAIL = "mohitkhare582@gmail.com"

  def up
    # Guard: public.admins must already exist (created by 0004_admins_and_helpers.sql).
    # If it doesn't, something is wrong with the migration order — raise clearly.
    result = execute("SELECT to_regclass('public.admins')").first
    if result["to_regclass"].nil?
      raise "public.admins does not exist — run db/migrations/0004_admins_and_helpers.sql first"
    end

    execute <<~SQL
      INSERT INTO public.admins (email, note)
      VALUES ('#{ADMIN_EMAIL}', 'owner')
      ON CONFLICT (email) DO NOTHING;
    SQL

    # Backfill users.admin for anyone already registered.
    execute <<~SQL
      UPDATE public.users u
         SET admin      = true,
             updated_at = now()
       WHERE u.email IN (SELECT email FROM public.admins)
         AND u.admin = false;
    SQL
  end

  def down
    execute <<~SQL
      UPDATE public.users
         SET admin      = false,
             updated_at = now()
       WHERE email = '#{ADMIN_EMAIL}';
    SQL
    # Intentionally do NOT delete from public.admins — that table is managed
    # by the legacy SQL migration suite and may still be referenced by the
    # old GoTrue-based stack during the transition window.
  end
end
