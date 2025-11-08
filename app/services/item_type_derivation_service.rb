# Service for deriving item type from category hierarchy
class ItemTypeDerivationService
  def self.derive_from_category(category)
    return nil unless category

    # Navigate to top-level category
    node = category
    if node.respond_to?(:parent_id) && node.parent_id.present?
      while node.parent_id.present?
        node = node.respond_to?(:parent_category) ? node.parent_category : node.parent
      end
      # Derive type from top-level category name
      return category_type_from_name(node.name)
    end

    # Derive type from category name
    category_type_from_name(node.name)
  end

  def self.category_type_from_name(name)
    down = name.to_s.downcase
    return "clothing" if %w[tops bottoms dresses outerwear undergarments shirts pants t-shirts sweaters jackets coats jeans skirts].any? { |p| down.start_with?(p) }
    return "shoes" if %w[athletic dress shoes casual boots sneakers loafers sandals running training oxfords heels].any? { |p| down.start_with?(p) }
    return "accessories" if %w[bags belts hats scarves sunglasses clutches totes backpacks beanies fedoras].any? { |p| down.start_with?(p) }
    return "jewelry" if %w[necklaces rings earrings bracelets watches].any? { |p| down.start_with?(p) }
    "clothing"
  end
end
