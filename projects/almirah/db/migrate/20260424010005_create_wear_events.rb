# frozen_string_literal: true

# project_almirah.wear_events — log of every time an item was worn.
# attendees is a text[] so that repeat-risk queries can use the overlap operator:
#   WHERE ARRAY['Meera'] && attendees
# No normalisation of attendee names in v1 — free text is sufficient for
# personal-scale use.
class CreateWearEvents < ActiveRecord::Migration[8.0]
  def up
    execute <<~SQL
      CREATE TABLE IF NOT EXISTS project_almirah.wear_events (
        id         UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
        item_id    UUID        NOT NULL
                     REFERENCES project_almirah.items (id) ON DELETE CASCADE,
        worn_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        event_name TEXT,
        attendees  TEXT[]      NOT NULL DEFAULT '{}',
        notes      TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );

      -- Primary access pattern: all wear events for a given item in date order.
      CREATE INDEX IF NOT EXISTS idx_wear_events_item_worn_at
        ON project_almirah.wear_events (item_id, worn_at DESC);

      -- GIN index for attendee overlap queries (repeat-risk).
      CREATE INDEX IF NOT EXISTS idx_wear_events_attendees
        ON project_almirah.wear_events USING gin (attendees);
    SQL
  end

  def down
    execute "DROP TABLE IF EXISTS project_almirah.wear_events;"
  end
end
