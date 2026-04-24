# frozen_string_literal: true

# Read-only ActiveRecord model for public.projects.
# This table is owned by the SQL migration suite (not by Rails).
# We never issue CREATE/ALTER/DROP against it from here.
class Project < ApplicationRecord
  self.table_name = "public.projects"
  # Disable STI — the "type" column does not exist here.
  self.inheritance_column = nil

  # Available status values, matching the status-chip brand component.
  STATUS_VALUES = %w[live wip paused archived open-source].freeze

  # Derive display status — prefer the status column, fall back to live_at presence.
  def derived_status
    return status if status.present? && STATUS_VALUES.include?(status)
    live_at.present? ? "live" : "wip"
  end

  # Path-routed link: /almirah instead of https://almirah.sastaspace.com
  def path_link
    "/#{slug}"
  end
end
