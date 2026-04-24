class User < ApplicationRecord
  has_secure_password validations: false  # Google-auth users have no password to validate
  has_many :sessions, dependent: :destroy

  # Almirah associations (cross-schema — project_almirah tables)
  has_many :items,       class_name: "Item",      foreign_key: "user_id", dependent: :destroy
  has_many :outfits,     class_name: "Outfit",    foreign_key: "user_id", dependent: :destroy
  has_many :ingest_jobs, class_name: "IngestJob", foreign_key: "user_id", dependent: :destroy

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

  def admin?
    !!admin
  end
end
