require "test_helper"

class ServicesTest < ActiveSupport::TestCase
  test "Services module exists" do
    assert defined?(Services)
    assert_kind_of Module, Services
  end

  test "Services module can be included" do
    # Verify the module can be used
    test_class = Class.new do
      include Services
    end
    assert test_class.included_modules.include?(Services)
  end
end
