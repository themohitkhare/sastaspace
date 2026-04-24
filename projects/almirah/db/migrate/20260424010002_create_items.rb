# frozen_string_literal: true

# project_almirah.items — one row per wardrobe item.
#
# Design notes:
#   - id is UUID (gen_random_uuid()) — safe to generate client-side or in the
#     seed script without a sequence; also stable across DB restores.
#   - user_id references public.users via a cross-schema FK.  Postgres supports
#     this natively; no extra search_path games needed for the constraint.
#   - last_worn_at is nullable (item may never have been worn since catalogued).
#   - photo_path is a plain string for Active Storage key or file path; Active
#     Storage blob associations are layered on top at the Rails model level,
#     not at the DB level — no migration needed for that.
#   - Unique index on (user_id, id) satisfies the requirement while also
#     enabling efficient "all items for user X" scans via index-only scan.
class CreateItems < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.items (
        id           UUID        NOT NULL DEFAULT gen_random_uuid(),
        user_id      BIGINT      NOT NULL
                       REFERENCES public.users (id) ON DELETE CASCADE,
        kind         TEXT        NOT NULL,
        name         TEXT        NOT NULL,
        tone         TEXT        NOT NULL,
        rack         TEXT        NOT NULL,
        last_worn_at TIMESTAMPTZ,
        wears_count  INTEGER     NOT NULL DEFAULT 0 CHECK (wears_count >= 0),
        price_inr    INTEGER     CHECK (price_inr >= 0),
        photo_path   TEXT,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (id)
      );

      -- kind and rack are low-cardinality text fields — CHECK constraints are
      -- simpler than enums here (easier to extend without ALTER TYPE migrations).
      ALTER TABLE project_almirah.items
        ADD CONSTRAINT items_kind_check CHECK (
          kind IN ('kurta','saree','blouse','dupatta','sherwani',
                   'shirt','jeans','lehenga','juttis','jacket')
        );

      ALTER TABLE project_almirah.items
        ADD CONSTRAINT items_rack_check CHECK (
          rack IN ('ethnic','office','weekend')
        );

      -- Covering index for the most common query: all items for a user.
      CREATE UNIQUE INDEX IF NOT EXISTS idx_items_user_id_id
        ON project_almirah.items (user_id, id);

      -- Support last-worn ordering without a full scan.
      CREATE INDEX IF NOT EXISTS idx_items_user_last_worn
        ON project_almirah.items (user_id, last_worn_at DESC NULLS LAST);

      -- Support rack-filtered views.
      CREATE INDEX IF NOT EXISTS idx_items_user_rack
        ON project_almirah.items (user_id, rack);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.items;"
  end
end
