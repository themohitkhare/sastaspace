# frozen_string_literal: true

# Seed migration: loads the 26 items + 3 gap suggestions from
# projects/almirah/web/src/lib/almirah/items.ts into the database.
#
# Idempotency: all inserts use ON CONFLICT (id) DO NOTHING so replaying this
# migration on a DB that already has the rows is a safe no-op.
#
# lastWorn strings from the TypeScript source are converted to approximate
# TIMESTAMPTZ values relative to the migration timestamp (2026-04-24).
# The mapping is intentionally lossy (e.g. "1y" → 1 year ago to the day)
# but sufficient — these are historical display values, not audit records.
#
# user_id handling: the seed targets the first admin user found in
# public.users.  If no user exists yet (fresh DB before first sign-in)
# the seed is skipped with a NOTICE — re-run after first Google login.
class SeedAlmirahItems < ActiveRecord::Migration[8.0]
  # Converts the lastWorn shorthand from items.ts to an approximate interval.
  LAST_WORN_OFFSETS = {
    "1d"  => "1 day",
    "2d"  => "2 days",
    "3d"  => "3 days",
    "4d"  => "4 days",
    "5d"  => "5 days",
    "6d"  => "6 days",
    "8d"  => "8 days",
    "1w"  => "7 days",
    "2w"  => "14 days",
    "3w"  => "21 days",
    "1mo" => "30 days",
    "2mo" => "60 days",
    "3mo" => "90 days",
    "4mo" => "120 days",
    "5mo" => "150 days",
    "6mo" => "180 days",
    "8mo" => "240 days",
    "1y"  => "365 days",
  }.freeze

  # 26 items transcribed verbatim from items.ts ITEMS array.
  ITEMS = [
    # ETHNIC rack
    { id: "i01", kind: "kurta",    name: "ivory chikankari kurta",    tone: "cream",  rack: "ethnic",  last_worn: "3w",  wears: 11, price: 2400 },
    { id: "i02", kind: "kurta",    name: "indigo block-print kurta",  tone: "indigo", rack: "ethnic",  last_worn: "6d",  wears: 14, price: 1800 },
    { id: "i03", kind: "kurta",    name: "rust linen kurta",          tone: "warm",   rack: "ethnic",  last_worn: "2mo", wears: 6,  price: 2100 },
    { id: "i04", kind: "kurta",    name: "black silk kurta",          tone: "ink",    rack: "ethnic",  last_worn: "4mo", wears: 3,  price: 3200 },
    { id: "i05", kind: "saree",    name: "red kanjivaram saree",      tone: "red",    rack: "ethnic",  last_worn: "5mo", wears: 3,  price: 18500 },
    { id: "i06", kind: "saree",    name: "olive banarasi saree",      tone: "olive",  rack: "ethnic",  last_worn: "8mo", wears: 2,  price: 9200 },
    { id: "i07", kind: "saree",    name: "sky chiffon saree",         tone: "indigo", rack: "ethnic",  last_worn: "1y",  wears: 1,  price: 4200 },
    { id: "i08", kind: "lehenga",  name: "rose mirror-work lehenga",  tone: "rose",   rack: "ethnic",  last_worn: "3mo", wears: 2,  price: 12500 },
    { id: "i09", kind: "blouse",   name: "gold brocade blouse",       tone: "warm",   rack: "ethnic",  last_worn: "5mo", wears: 3,  price: 1600 },
    { id: "i10", kind: "blouse",   name: "olive zari blouse",         tone: "olive",  rack: "ethnic",  last_worn: "8mo", wears: 2,  price: 1800 },
    { id: "i11", kind: "dupatta",  name: "cream bandhani dupatta",    tone: "cream",  rack: "ethnic",  last_worn: "2w",  wears: 9,  price: 1200 },
    { id: "i12", kind: "dupatta",  name: "rose gota dupatta",         tone: "rose",   rack: "ethnic",  last_worn: "3mo", wears: 2,  price: 2100 },
    { id: "i13", kind: "sherwani", name: "navy embroidered sherwani", tone: "navy",   rack: "ethnic",  last_worn: "5mo", wears: 1,  price: 14000 },
    { id: "i14", kind: "juttis",   name: "cream embroidered juttis",  tone: "cream",  rack: "ethnic",  last_worn: "2w",  wears: 8,  price: 1400 },
    { id: "i15", kind: "juttis",   name: "red wedding juttis",        tone: "red",    rack: "ethnic",  last_worn: "5mo", wears: 2,  price: 1800 },
    # OFFICE rack
    { id: "i20", kind: "shirt",    name: "white oxford shirt",        tone: "cream",  rack: "office",  last_worn: "2d",  wears: 22, price: 1500 },
    { id: "i21", kind: "shirt",    name: "sand linen shirt",          tone: "sand",   rack: "office",  last_worn: "5d",  wears: 9,  price: 1900 },
    { id: "i22", kind: "shirt",    name: "indigo oxford shirt",       tone: "indigo", rack: "office",  last_worn: "1w",  wears: 13, price: 1700 },
    { id: "i23", kind: "jacket",   name: "charcoal blazer",           tone: "ink",    rack: "office",  last_worn: "3w",  wears: 6,  price: 5400 },
    { id: "i24", kind: "jeans",    name: "tailored black trousers",   tone: "ink",    rack: "office",  last_worn: "4d",  wears: 18, price: 2800 },
    { id: "i25", kind: "jeans",    name: "beige chinos",              tone: "sand",   rack: "office",  last_worn: "8d",  wears: 11, price: 2400 },
    # WEEKEND rack
    { id: "i30", kind: "shirt",    name: "faded green tee",           tone: "green",  rack: "weekend", last_worn: "3d",  wears: 21, price: 600 },
    { id: "i31", kind: "shirt",    name: "cream band tee",            tone: "cream",  rack: "weekend", last_worn: "1d",  wears: 28, price: 800 },
    { id: "i32", kind: "jeans",    name: "dark wash jeans",           tone: "denim",  rack: "weekend", last_worn: "2d",  wears: 34, price: 2800 },
    { id: "i33", kind: "jeans",    name: "light wash straight jeans", tone: "denim",  rack: "weekend", last_worn: "5d",  wears: 18, price: 2500 },
    { id: "i34", kind: "jacket",   name: "denim trucker jacket",      tone: "denim",  rack: "weekend", last_worn: "3w",  wears: 7,  price: 3400 },
  ].freeze

  GAP_SUGGESTIONS = [
    { id: "g1", kind: "kurta",  name: "mustard cotton kurta",   tone: "warm", reason: "rounds out your ethnic-daily rack — you skew cool-toned",               source: "Myntra", price: 1899, url: "https://www.myntra.com/kurta/mustard-cotton" },
    { id: "g2", kind: "blouse", name: "maroon raw-silk blouse", tone: "red",  reason: "your red saree has no matching blouse; you've reused the gold one 3x",   source: "Ajio",   price: 1299, url: "https://www.ajio.com/search/?text=maroon+silk+blouse" },
    { id: "g3", kind: "juttis", name: "black leather juttis",   tone: "ink",  reason: "a dark jutti would unlock the navy sherwani for low-key events",          source: "Amazon", price: 1650, url: "https://www.amazon.in/s?k=black+leather+juttis" },
  ].freeze

  def up
    # Resolve the admin user who should own the seed items.
    # Admin is defined by presence in public.admins allowlist (email_address match).
    result = execute(<<~SQL).first
      SELECT u.id
        FROM public.users u
        JOIN public.admins a ON a.email = u.email_address
       ORDER BY u.created_at
       LIMIT 1;
    SQL

    unless result
      say "WARNING: No admin user found (public.users joined on public.admins) — skipping item seed."
      say "Re-run this migration after the first Google sign-in creates a user row that matches public.admins."
      return
    end

    user_id = result["id"]
    say "Seeding #{ITEMS.size} items for user_id=#{user_id}"

    ITEMS.each do |item|
      interval  = LAST_WORN_OFFSETS.fetch(item[:last_worn], "0")
      execute <<~SQL
        INSERT INTO project_almirah.items
          (id, user_id, kind, name, tone, rack, last_worn_at, wears_count, price_inr, created_at, updated_at)
        VALUES (
          '#{item[:id]}',
          #{user_id},
          '#{item[:kind]}',
          '#{item[:name].gsub("'", "''")}',
          '#{item[:tone]}',
          '#{item[:rack]}',
          now() - INTERVAL '#{interval}',
          #{item[:wears]},
          #{item[:price]},
          now(),
          now()
        )
        ON CONFLICT (id) DO NOTHING;
      SQL
    end

    say "Seeding #{GAP_SUGGESTIONS.size} gap suggestions"

    GAP_SUGGESTIONS.each do |gs|
      execute <<~SQL
        INSERT INTO project_almirah.gap_suggestions
          (id, kind, name, tone, reason, source, price_inr, url, created_at, updated_at)
        VALUES (
          '#{gs[:id]}',
          '#{gs[:kind]}',
          '#{gs[:name].gsub("'", "''")}',
          '#{gs[:tone]}',
          '#{gs[:reason].gsub("'", "''")}',
          '#{gs[:source]}',
          #{gs[:price]},
          '#{gs[:url]}',
          now(),
          now()
        )
        ON CONFLICT (id) DO NOTHING;
      SQL
    end

    # Verify counts match expectations.
    items_count = execute("SELECT count(*) AS n FROM project_almirah.items WHERE user_id = #{user_id}").first["n"].to_i
    gaps_count  = execute("SELECT count(*) AS n FROM project_almirah.gap_suggestions").first["n"].to_i

    say "Items seeded: #{items_count} (expected >= 26)"
    say "Gap suggestions seeded: #{gaps_count} (expected >= 3)"

    raise "Item seed incomplete: got #{items_count}, expected 26" if items_count < 26
    raise "Gap suggestion seed incomplete: got #{gaps_count}, expected 3"  if gaps_count < 3
  end

  def down
    execute "DELETE FROM project_almirah.items WHERE id IN (#{ITEMS.map { |i| "'#{i[:id]}'" }.join(',')});"
    execute "DELETE FROM project_almirah.gap_suggestions WHERE id IN (#{GAP_SUGGESTIONS.map { |g| "'#{g[:id]}'" }.join(',')});"
  end
end
