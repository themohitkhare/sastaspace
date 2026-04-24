# db/seeds.rb — Almirah seed data.
#
# The 26 items + 3 gap suggestions are seeded via migration
# 20260424010008_seed_almirah_items.rb, which requires an admin user to exist
# in public.users before it can run.
#
# Running `bin/rails db:seed` is essentially a no-op for almirah — item data
# lives in the migration. This file adds the guard message so it is clear
# what to do if migrating a fresh database.

if !defined?(User) || User.where(admin: true).none?
  puts "========================================================================"
  puts "  Almirah seeds require at least one admin user in public.users."
  puts "  Sign in to sastaspace.com first, then re-run:"
  puts "    bin/rails db:migrate"
  puts "  (The seed migration 20260424010008 will auto-skip if re-replayed)"
  puts "========================================================================"
else
  admin = User.where(admin: true).first
  puts "Admin user exists (id=#{admin.id}, email=#{admin.email_address})."
  puts "Item seed is managed via migration 20260424010008_seed_almirah_items."
end
