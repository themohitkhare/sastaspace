# frozen_string_literal: true

# project_almirah.outfits — saved outfit combos (named collections of items).
# A user can save a multi-item combination under a name for quick re-use.
# Items in the outfit are tracked in project_almirah.outfit_items (join table).
class CreateOutfits < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.outfits (
        id         UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
        user_id    BIGINT      NOT NULL
                     REFERENCES public.users (id) ON DELETE CASCADE,
        name       TEXT        NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );

      CREATE INDEX IF NOT EXISTS idx_outfits_user_id
        ON project_almirah.outfits (user_id);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.outfits;"
  end
end
