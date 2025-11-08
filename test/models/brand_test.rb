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

  test "popular scope orders by name" do
    brand1 = create(:brand, name: "Brand B #{SecureRandom.hex(4)}")
    brand2 = create(:brand, name: "Brand A #{SecureRandom.hex(4)}")
    brand3 = create(:brand, name: "Brand C #{SecureRandom.hex(4)}")

    popular_brands = Brand.where(id: [ brand1.id, brand2.id, brand3.id ]).popular
    assert_equal [ brand2.id, brand1.id, brand3.id ], popular_brands.pluck(:id)
  end
end
