# frozen_string_literal: true

# project_almirah.gap_suggestions — curated "you should buy this" hints.
# Three rows seeded from items.ts; designed to be editable post-launch.
# Not tied to a user — these are global catalogue suggestions.
class CreateGapSuggestions < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.gap_suggestions (
        id         TEXT        NOT NULL PRIMARY KEY,
        kind       TEXT        NOT NULL,
        name       TEXT        NOT NULL,
        tone       TEXT        NOT NULL,
        reason     TEXT        NOT NULL,
        source     TEXT        NOT NULL,
        price_inr  INTEGER     NOT NULL CHECK (price_inr >= 0),
        url        TEXT        NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT gap_suggestions_kind_check CHECK (
          kind IN ('kurta','saree','blouse','dupatta','sherwani',
                   'shirt','jeans','lehenga','juttis','jacket')
        ),
        CONSTRAINT gap_suggestions_source_check CHECK (
          source IN ('Myntra','Ajio','Amazon')
        )
      );
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.gap_suggestions;"
  end
end
