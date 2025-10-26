class RefreshToken < ApplicationRecord
  belongs_to :user

  validates :token, presence: true, uniqueness: true
  validates :expires_at, presence: true

  # Scope to find active (non-blacklisted, not expired) refresh tokens
  scope :active, -> { where(blacklisted: false).where("expires_at > ?", Time.current) }
  scope :expired, -> { where("expires_at <= ?", Time.current) }
  scope :blacklisted, -> { where(blacklisted: true) }

  # Check if the token is still valid
  def active?
    !blacklisted && expires_at > Time.current
  end

  # Mark as blacklisted
  def blacklist!
    update!(blacklisted: true)
  end

  # Generate a secure random token
  def self.generate_token
    SecureRandom.urlsafe_base64(64)
  end

  # Create a new refresh token for a user
  def self.create_for_user!(user, expires_in: 30.days)
    create!(
      user: user,
      token: generate_token,
      expires_at: Time.current + expires_in,
      blacklisted: false
    )
  end
end
