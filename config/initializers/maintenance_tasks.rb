# Maintenance Tasks configuration
# See https://github.com/Shopify/maintenance_tasks for documentation

# Use ApplicationController as parent
# This ensures maintenance tasks use the same authentication as the main app
MaintenanceTasks.parent_controller = "ApplicationController"

# Track which user ran the task
MaintenanceTasks.metadata = ->() do
  { user_email: current_user&.email || "system" }
end
