# frozen_string_literal: true

require "application_system_test_case"

# home_unauth_test.rb
#
# Verifies the home page renders correctly for unauthenticated visitors.
#
# Expects a POSTGRES_URL pointing at a DB that has run:
#   make migrate   — creates public.projects, public.admins etc.
#   seed data      — landing row exists in public.projects
#
# If the DB has no rows the test still passes (empty-state branch renders).
# The project-card assertion uses a soft check: at least one of the possible
# states is true (card present OR empty-state present).
class HomeUnauthTest < ApplicationSystemTestCase
  test "root loads without application error when not authenticated" do
    visit root_url

    assert_no_text "Application Error"
    assert_no_text "We're sorry, but something went wrong"

    # Page should include the hero h1
    assert_selector "h1", text: /sasta lab/i
  end

  test "sign-in link is present on home page when not authenticated" do
    visit root_url

    # The link text reads "Sign in with Google"
    assert_selector "a", text: /sign in with google/i
  end

  test "projects section renders — either card grid or empty state" do
    visit root_url

    # The section is always present
    assert_selector "#projects"

    # Either at least one project card OR the empty-state message is shown
    has_cards  = page.has_selector?("a.group", wait: 2)
    has_empty  = page.has_text?("workshop's quiet today", wait: 1)

    assert has_cards || has_empty,
      "Expected either project cards or empty-state message in #projects section"
  end

  test "sign-in page shows Continue with Google button" do
    visit new_session_url

    assert_selector "form[action='/auth/google']", text: /Continue with Google/i
  end
end
