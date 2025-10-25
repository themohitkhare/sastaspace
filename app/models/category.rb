class Category < ApplicationRecord
  validates :name, presence: true, uniqueness: { scope: :parent_id }
  validates :slug, presence: true, uniqueness: true
  
  has_many :inventory_items, dependent: :restrict_with_exception
  has_many :subcategories, class_name: 'Category', foreign_key: 'parent_id', dependent: :destroy
  belongs_to :parent_category, class_name: 'Category', foreign_key: 'parent_id', optional: true
  
  before_validation :generate_slug, if: -> { name.present? && slug.blank? }
  
  # Hierarchical scopes
  scope :root_categories, -> { where(parent_id: nil) }
  scope :subcategories_of, ->(parent) { where(parent_id: parent.id) }
  scope :active, -> { where(active: true) }
  scope :ordered, -> { order(:sort_order, :name) }
  
  # Tree navigation
  def ancestors
    return [] if parent_category.nil?
    parent_category.ancestors + [parent_category]
  end
  
  def descendants
    subcategories + subcategories.flat_map(&:descendants)
  end
  
  def root?
    parent_id.nil?
  end
  
  def leaf?
    subcategories.empty?
  end
  
  # Full path for display
  def full_path
    (ancestors + [self]).map(&:name).join(' > ')
  end
  
  # Item count including subcategories
  def total_item_count(user = nil)
    if user
      categories = [self] + descendants
      user.inventory_items.where(category: categories).count
    else
      0
    end
  end
  
  private
  
  def generate_slug
    base_slug = name.parameterize
    counter = 1
    self.slug = base_slug
    
    while Category.exists?(slug: slug)
      self.slug = "#{base_slug}-#{counter}"
      counter += 1
    end
  end
end
