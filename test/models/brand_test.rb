require "test_helper"

class BrandTest < ActiveSupport::TestCase
  def setup
    @brand = build(:brand)
  end

  test "should be valid" do
    assert @brand.valid?
  end

  test "name should be present" do
    @brand.name = nil
    assert_not @brand.valid?
    assert_includes @brand.errors[:name], "can't be blank"
  end

  test "name should be unique" do
    @brand.save!
    duplicate_brand = build(:brand, name: @brand.name)
    assert_not duplicate_brand.valid?
    assert_includes duplicate_brand.errors[:name], "has already been taken"
  end

  test "should restrict destroy when inventory items exist" do
    brand = create(:brand)
    create(:inventory_item, brand: brand)

    assert_raises(ActiveRecord::DeleteRestrictionError) do
      brand.destroy
    end
  end
end
