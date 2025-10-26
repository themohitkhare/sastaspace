module Api
  module V1
    class CategorySerializer
      def initialize(category, options = {})
        @category = category
        @options = options
        @include_children = options[:include_children] || false
        @include_item_count = options[:include_item_count] || false
        @user = options[:user]
      end

      def as_json
        result = {
          id: @category.id,
          name: @category.name,
          slug: @category.slug,
          description: @category.description,
          sort_order: @category.sort_order,
          active: @category.active,
          metadata: @category.metadata,
          parent_id: @category.parent_id,
          full_path: @category.full_path,
          is_root: @category.root?,
          is_leaf: @category.leaf?,
          created_at: @category.created_at.iso8601,
          updated_at: @category.updated_at.iso8601
        }

        # Add item count if requested
        if @include_item_count
          result[:item_count] = @category.total_item_count(@user)
        end

        # Add children if requested
        if @include_children
          result[:children] = @category.subcategories.active.ordered.map do |child|
            CategorySerializer.new(child, @options).as_json
          end
        end

        result
      end

      # Class method for serializing multiple categories
      def self.serialize_collection(categories, options = {})
        categories.map { |category| new(category, options).as_json }
      end

      # Class method for serializing category tree
      def self.serialize_tree(categories, options = {})
        categories.map do |category|
          new(category, options.merge(include_children: true)).as_json
        end
      end
    end
  end
end
