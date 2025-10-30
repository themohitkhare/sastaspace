require "application_system_test_case"

class InventoryWizardSubmitTest < ApplicationSystemTestCase
  setup do
    @user = create(:user, password: "Password123!")
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"
  end

  test "submit button appears on final step and next is hidden" do
    @category = create(:category, :clothing)
    visit "/inventory_items/new"

    # Step 1
    select "Clothing", from: "Item Type"
    find("input[name='inventory_item[category_id]']", visible: false).set(@category.id)
    find("button[data-form-wizard-target='nextButton']").click

    # Step 2
    fill_in "Name", with: "Wizard Submit Check"
    find("button[data-form-wizard-target='nextButton']").click

    # Step 3
    find("button[data-form-wizard-target='nextButton']").click

    # Step 4 - verify Next hidden and Submit visible
    assert_no_selector "button[data-form-wizard-target='nextButton']", wait: 5, visible: true
    assert_selector "input[type='submit'][data-form-wizard-target='submitButton']:not(.hidden)", wait: 5
  end
end
