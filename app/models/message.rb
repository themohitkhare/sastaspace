class Message < ApplicationRecord
  acts_as_message
  has_many_attached :attachments

  # Note: Turbo Streams broadcasting can be enabled later if needed
  # after_create_commit -> { broadcast_append_to chat, partial: "messages/message", locals: { message: self } }
end
