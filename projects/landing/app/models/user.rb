class User < ApplicationRecord
  has_secure_password validations: false  # Google-auth users have no password to validate
  has_many :sessions, dependent: :destroy

  normalizes :email_address, with: ->(e) { e.strip.downcase }

  validates :email_address, presence: true, uniqueness: { case_sensitive: false },
                            format: { with: URI::MailTo::EMAIL_REGEXP }

  # OAuth columns — nil for email+password users, populated for Google users.
  # provider: "google" | nil
  # uid: google sub claim
  # name: display name from Google profile
  attribute :provider, :string
  attribute :uid,      :string
  attribute :name,     :string

  def google?
    provider == "google"
  end

  # Admin gate — joins against public.admins allowlist.
  # Returns false (not nil) when admins table is empty or email not found,
  # so the app renders normally even with an empty allowlist.
  def admin?
    Admin.exists?(email: email_address)
  rescue ActiveRecord::StatementInvalid
    # Guard: if admins table doesn't exist yet (fresh env before migrations),
    # degrade gracefully — no user is admin, app still renders.
    false
  end
end
