require "test_helper"

class InventoryItemMiscMethodsTest < ActiveSupport::TestCase
  test "metadata_summary returns empty hash when metadata is nil" do
    item = build(:inventory_item, metadata: nil)
    assert_equal({}, item.metadata_summary)
  end
end


