# Concern for item type derivation logic
module TypeDerivable
  extend ActiveSupport::Concern

  # Backward-compatibility for legacy tests/serializers expecting `item_type`
  def item_type
    # If explicitly overridden to nil, honor that (used by tests)
    if defined?(@item_type_overridden) && @item_type_overridden && @virtual_item_type.nil?
      return nil
    end
    return @virtual_item_type if @virtual_item_type.present?
    top_level_category
  end

  # Writer is a no-op retained for compatibility to avoid NoMethodError in tests
  def item_type=(value)
    @item_type_overridden = true
    @virtual_item_type = value.presence
  end

  private

  def top_level_category
    ItemTypeDerivationService.derive_from_category(category)
  end
end
