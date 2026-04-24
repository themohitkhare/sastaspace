# frozen_string_literal: true

require "application_system_test_case"

# admin_gate_test.rb
#
# Verifies the /admin route is gated correctly:
#   - Non-admin signed-in user → 302 redirect to /
#   - Admin user → 200 with "coming soon" content
#
# Requires the public.admins table to contain mohitkhare582@gmail.com
# (seeded by SeedAdmins migration / make migrate).
class AdminGateTest < ApplicationSystemTestCase
  teardown do
    sign_out_omniauth
  end

  test "non-admin signed-in user hitting /admin is redirected to root" do
    sign_in_as_google(email: "regularuser@example.com")

    # Attempt to visit /admin
    visit admin_root_url

    # Should be redirected to root, not the admin page
    assert_current_path root_path

    # The admin coming-soon page should not be visible
    refute_selector "h1", text: "Admin"
  end

  test "admin user visiting /admin sees the coming-soon admin page" do
    # The owner email is in public.admins — seeded by SeedAdmins migration.
    sign_in_as_google(email: "mohitkhare582@gmail.com", name: "Mohit Khare")

    visit admin_root_url

    # Should stay on /admin
    assert_current_path admin_root_path

    # Should show the coming-soon message
    assert_text "coming soon"
  end
end
