class AddHierarchicalFieldsToCategories < ActiveRecord::Migration[8.1]
  def change
    add_reference :categories, :parent, foreign_key: { to_table: :categories }, null: true
    add_column :categories, :slug, :string, null: false, default: ''
    add_column :categories, :sort_order, :integer, default: 0
    add_column :categories, :active, :boolean, default: true
    add_column :categories, :metadata, :json, default: {}

    # Update existing categories to have slugs before adding unique index
    reversible do |dir|
      dir.up do
        Category.find_each do |category|
          base_slug = category.name.parameterize
          counter = 1
          slug = base_slug

          while Category.exists?(slug: slug)
            slug = "#{base_slug}-#{counter}"
            counter += 1
          end

          category.update_column(:slug, slug)
        end
      end
    end

    add_index :categories, :slug, unique: true
    add_index :categories, [ :parent_id, :sort_order ]
    add_index :categories, :active
  end
end
