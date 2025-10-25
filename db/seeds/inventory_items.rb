# Seed file for Inventory Items system
puts "Seeding categories..."

# Create clothing categories
Category::CLOTHING_CATEGORIES.each do |category_name|
  Category.find_or_create_by(name: category_name) do |category|
    category.description = "Category for #{category_name} clothing items"
  end
end

# Create shoes categories
Category::SHOES_CATEGORIES.each do |category_name|
  Category.find_or_create_by(name: category_name) do |category|
    category.description = "Category for #{category_name} shoes"
  end
end

# Create accessories categories
Category::ACCESSORIES_CATEGORIES.each do |category_name|
  Category.find_or_create_by(name: category_name) do |category|
    category.description = "Category for #{category_name} accessories"
  end
end

# Create jewelry categories
Category::JEWELRY_CATEGORIES.each do |category_name|
  Category.find_or_create_by(name: category_name) do |category|
    category.description = "Category for #{category_name} jewelry"
  end
end

puts "Seeding brands..."

# Create some popular brands
brands = [
  "Nike", "Adidas", "Zara", "H&M", "Uniqlo", "Gap", "Levi's", "Calvin Klein",
  "Tommy Hilfiger", "Ralph Lauren", "Gucci", "Prada", "Chanel", "Louis Vuitton",
  "Apple", "Samsung", "Sony", "Bose", "Ray-Ban", "Oakley"
]

brands.each do |brand_name|
  Brand.find_or_create_by(name: brand_name) do |brand|
    brand.description = "Popular #{brand_name} brand"
  end
end

puts "Seeding tags..."

# Create some common tags
tags = [
  "casual", "formal", "work", "party", "sport", "comfortable", "stylish",
  "vintage", "modern", "classic", "trendy", "minimalist", "colorful",
  "neutral", "summer", "winter", "spring", "fall", "cotton", "denim",
  "leather", "silk", "wool", "sustainable", "eco-friendly"
]

tags.each do |tag_name|
  Tag.find_or_create_by(name: tag_name) do |tag|
    tag.color = "#3B82F6" # Default blue color
  end
end

puts "Seeding completed!"
