# frozen_string_literal: true

# project_almirah.ingest_jobs — tracks bulk photo ingest operations.
# Solid Queue (Rails 8 default) manages the actual job queue; this table is
# the persistent record / status board that the UI polls.
#
# Status uses a TEXT column with a CHECK constraint rather than a Postgres
# ENUM.  Rationale: adding a new status (e.g. 'cancelled') with an ENUM
# requires ALTER TYPE which locks the table; a CHECK constraint on TEXT can
# be dropped and re-created without a lock in Postgres 12+.
class CreateIngestJobs < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.ingest_jobs (
        id            UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
        user_id       BIGINT      NOT NULL
                        REFERENCES public.users (id) ON DELETE CASCADE,
        photo_count   INTEGER     NOT NULL DEFAULT 0 CHECK (photo_count >= 0),
        status        TEXT        NOT NULL DEFAULT 'queued',
        started_at    TIMESTAMPTZ,
        finished_at   TIMESTAMPTZ,
        error_message TEXT,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT ingest_jobs_status_check
          CHECK (status IN ('queued','processing','done','error'))
      );

      CREATE INDEX IF NOT EXISTS idx_ingest_jobs_user_id_status
        ON project_almirah.ingest_jobs (user_id, status);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.ingest_jobs;"
  end
end
