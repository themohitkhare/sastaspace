# Service for item validation logic
class ItemValidationService
  def self.validate_type_specific_fields(item)
    case item.item_type
    when "clothing"
      validate_clothing_fields(item)
    when "shoes"
      validate_shoes_fields(item)
    when "accessories"
      validate_accessories_fields(item)
    when "jewelry"
      validate_jewelry_fields(item)
    end
  end

  def self.validate_item_type_presence(item)
    item.errors.add(:item_type, "can't be blank") if item.item_type.blank?
  end

  def self.valid_clothing_size?(size)
    return true if size.blank?
    %w[XS S M L XL XXL].include?(size) || size.match?(/\d+/)
  end

  def self.valid_shoe_size?(size)
    return true if size.blank?
    size.match?(/\d+(\.\d+)?/) && size.to_f.between?(3, 15)
  end

  private

  def self.validate_clothing_fields(item)
    # Clothing-specific validations
    if item.size.present? && !valid_clothing_size?(item.size)
      item.errors.add(:size, "is not a valid clothing size")
    end
  end

  def self.validate_shoes_fields(item)
    # Shoes-specific validations
    if item.size.present? && !valid_shoe_size?(item.size)
      item.errors.add(:size, "is not a valid shoe size")
    end
  end

  def self.validate_accessories_fields(item)
    # Accessories-specific validations
  end

  def self.validate_jewelry_fields(item)
    # Jewelry-specific validations
  end
end
