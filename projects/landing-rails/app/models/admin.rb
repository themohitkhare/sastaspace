# frozen_string_literal: true

# Read-only model for public.admins.
# This table is owned by the SQL migration suite (0004_admins_and_helpers.sql).
# We never issue DDL against it; we only read from it.
#
# Table shape:
#   email (text, primary key)
#   note  (text, nullable)
#   added_at (timestamp)
class Admin < ApplicationRecord
  self.table_name = "public.admins"
  self.primary_key = "email"

  # No timestamps managed by Rails — the table has its own added_at column.
  self.record_timestamps = false
end
