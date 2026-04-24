# frozen_string_literal: true

# project_almirah.outfit_items — join table between outfits and items.
# position allows ordered display within the outfit (e.g. base layer first).
#
# Both FKs reference tables in project_almirah schema.
# No separate PK column — (outfit_id, item_id) is the natural composite PK.
class CreateOutfitItems < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.outfit_items (
        outfit_id  UUID    NOT NULL
                     REFERENCES project_almirah.outfits (id) ON DELETE CASCADE,
        item_id    UUID    NOT NULL
                     REFERENCES project_almirah.items  (id) ON DELETE CASCADE,
        position   INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (outfit_id, item_id)
      );

      -- Index to look up "which outfits contain item X" (reverse join).
      CREATE INDEX IF NOT EXISTS idx_outfit_items_item_id
        ON project_almirah.outfit_items (item_id);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.outfit_items;"
  end
end
