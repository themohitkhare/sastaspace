# frozen_string_literal: true

# Creates the project_almirah Postgres schema.
# Must run before any other almirah migration.
# Safe to re-run: CREATE SCHEMA IF NOT EXISTS is idempotent.
class CreateAlmirahSchema < ActiveRecord::Migration[8.0]
  def up
    execute "CREATE SCHEMA IF NOT EXISTS project_almirah;"

    # Grant the Rails DB role access to the new schema.
    # The role name is injected via DATABASE_URL / database.yml at deploy time.
    # Default fallback is 'postgres' (works for local dev and the supabase image).
    execute <<~SQL
      DO $$
      DECLARE
        r TEXT;
      BEGIN
        FOR r IN SELECT unnest(ARRAY['anon', 'authenticated', 'service_role'])
        LOOP
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('GRANT USAGE ON SCHEMA project_almirah TO %I', r);
          END IF;
        END LOOP;
      END $$;
    SQL
  end

  def down
    # Only drop if empty — refuse to silently nuke data.
    result = execute(<<~SQL).first
      SELECT count(*)::int AS n
        FROM information_schema.tables
       WHERE table_schema = 'project_almirah';
    SQL
    if result["n"].to_i > 0
      raise "project_almirah schema is not empty — drop tables first before rolling back CreateAlmirahSchema"
    end

    execute "DROP SCHEMA IF EXISTS project_almirah;"
  end
end
