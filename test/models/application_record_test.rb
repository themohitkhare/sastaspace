require "test_helper"

class ApplicationRecordTest < ActiveSupport::TestCase
  test "ApplicationRecord is a subclass of ActiveRecord::Base" do
    assert_equal ActiveRecord::Base, ApplicationRecord.superclass
  end

  test "ApplicationRecord can be used as base class" do
    # Verify that models inherit from ApplicationRecord
    assert_equal ApplicationRecord, InventoryItem.superclass
    assert_equal ApplicationRecord, User.superclass
  end
end
