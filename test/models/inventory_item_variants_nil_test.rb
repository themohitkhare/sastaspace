require "test_helper"

class InventoryItemVariantsNilTest < ActiveSupport::TestCase
  test "primary_image_variants returns empty hash when no image attached" do
    item = build(:inventory_item)
    assert_equal({}, item.primary_image_variants)
  end
end


