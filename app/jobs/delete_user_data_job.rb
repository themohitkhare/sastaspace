# GDPR Account Deletion Job
# Implements "Right to be Forgotten" (GDPR Article 17)
# Permanently deletes all user data
class DeleteUserDataJob < ApplicationJob
  queue_as :default

  def perform(user_id)
    user = User.find_by(id: user_id)
    return unless user # User may already be deleted

    email = user.email # Store for logging before deletion

    Rails.logger.info "Starting GDPR account deletion for user #{user_id} (#{email})"

    # Delete in order to respect foreign key constraints
    # 1. Delete dependent records first
    user.ai_analyses.destroy_all
    user.outfits.each do |outfit|
      outfit.outfit_items.destroy_all
    end
    user.outfits.destroy_all
    user.inventory_items.each do |item|
      # Delete attached images
      item.primary_image.purge if item.primary_image.attached?
      item.additional_images.purge if item.additional_images.attached?
      # Delete tags associations
      item.inventory_tags.destroy_all
    end
    user.inventory_items.destroy_all

    # 2. Invalidate all refresh tokens
    user.refresh_tokens.update_all(blacklisted: true)

    # 3. Delete user account (cascades to remaining associations)
    user.destroy!

    Rails.logger.info "GDPR account deletion completed for user #{user_id} (#{email})"
  rescue ActiveRecord::RecordNotFound
    Rails.logger.warn "User #{user_id} not found during deletion - may have already been deleted"
  rescue StandardError => e
    Rails.logger.error "GDPR account deletion failed for user #{user_id}: #{e.message}"
    Rails.logger.error e.backtrace.first(10).join("\n")
    raise e # Re-raise to trigger retry mechanism
  end
end
