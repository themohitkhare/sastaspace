# Example migration to create an admin user
# Run this migration to set up your first admin user
#
# Usage:
#   rails db:migrate
#   rails runner "User.find_by(email: 'admin@example.com').update_column(:admin, true)"
#
# Or use direct SQL:
#   UPDATE users SET admin = true WHERE email = 'admin@example.com';
#
# NOTE: This is an example file. You should create your own migration
# or use Rails console with update_column (bypasses validations and callbacks)

class CreateAdminUserExample < ActiveRecord::Migration[8.1]
  def up
    # This is just an example - you should create your own migration
    # or use Rails console with update_column
    # Example:
    # user = User.find_by(email: 'admin@example.com')
    # user.update_column(:admin, true) if user
  end

  def down
    # Remove admin status
    # User.where(admin: true).update_all(admin: false)
  end
end
