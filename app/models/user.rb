class User < ApplicationRecord
  has_secure_password

  validates :email, presence: true, uniqueness: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, presence: true,
                      length: { minimum: 8 },
                      format: {
                        with: /\A(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*\z/,
                        message: "must contain at least one uppercase letter, one lowercase letter, and one number"
                      },
                      on: :create
  validates :password_confirmation, presence: true, on: :create
  validates :first_name, presence: true
  validates :last_name, presence: true

  has_many :inventory_items, dependent: :destroy
  has_many :outfits, dependent: :destroy
  has_many :ai_analyses, dependent: :destroy
  has_many :refresh_tokens, dependent: :destroy
  has_many :failed_login_attempts, dependent: :destroy

  # Invalidate all refresh tokens when password changes
  before_save :invalidate_refresh_tokens_on_password_change

  # Invalidate all refresh tokens for this user (e.g., on password change)
  def invalidate_all_refresh_tokens!
    refresh_tokens.update_all(blacklisted: true)
  end

  def full_name
    [ first_name, last_name ].compact.join(" ").presence || email
  end

  private

  def invalidate_refresh_tokens_on_password_change
    return unless password_digest_changed?

    # Invalidate all refresh tokens when password changes
    invalidate_all_refresh_tokens!
  end
end
