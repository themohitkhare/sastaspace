# Tracks failed login attempts for account lockout security
class FailedLoginAttempt < ApplicationRecord
  belongs_to :user, optional: true

  # Lockout configuration
  MAX_ATTEMPTS = 5
  LOCKOUT_DURATION = 15.minutes

  # Scope to find recent failed attempts
  scope :recent, -> { where("failed_at > ?", LOCKOUT_DURATION.ago) }
  scope :for_user, ->(user) { where(user: user) }
  scope :for_email, ->(email) { joins(:user).where(users: { email: email }) }
  scope :for_ip, ->(ip) { where(ip_address: ip) }

  # Check if account should be locked
  def self.account_locked?(user_or_email, ip_address = nil)
    attempts = if user_or_email.is_a?(User)
                 for_user(user_or_email).recent
    else
                 for_email(user_or_email).recent
    end

    # Also check by IP if provided
    if ip_address.present?
      ip_attempts = for_ip(ip_address).recent
      if ip_attempts.any?
        attempts = attempts.any? ? attempts.or(ip_attempts) : ip_attempts
      end
    end

    attempts.any? ? attempts.count >= MAX_ATTEMPTS : false
  end

  # Record a failed login attempt
  def self.record_failure(user_or_email, ip_address = nil)
    user = user_or_email.is_a?(User) ? user_or_email : User.find_by(email: user_or_email)

    create!(
      user: user,
      ip_address: ip_address,
      failed_at: Time.current
    )

    # Clean up old attempts (older than lockout duration)
    cleanup_old_attempts
  end

  # Clear failed attempts for a user (on successful login)
  def self.clear_for_user(user)
    for_user(user).delete_all
  end

  # Clear failed attempts for an IP
  def self.clear_for_ip(ip_address)
    for_ip(ip_address).delete_all
  end

  private

  def self.cleanup_old_attempts
    where("failed_at < ?", LOCKOUT_DURATION.ago).delete_all
  end
end
