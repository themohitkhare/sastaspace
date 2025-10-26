class Chat < ApplicationRecord
  acts_as_chat

  # Associate chats with users for multi-tenancy
  belongs_to :user, optional: true

  # Note: Turbo Streams broadcasting can be enabled later if needed
  # after_create_commit -> { broadcast_prepend_to "chats" }
  # after_update_commit -> { broadcast_replace_to "chats" }
  # after_destroy_commit -> { broadcast_remove_to "chats" }
end
