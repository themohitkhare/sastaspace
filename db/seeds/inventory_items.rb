# Seed file for Inventory Items system
puts "Seeding hierarchical categories..."

def create_category_taxonomy
  # Root Categories
  clothing = Category.find_or_create_by(name: 'Clothing') do |cat|
    cat.description = 'All wearable garments'
    cat.sort_order = 1
  end
  
  shoes = Category.find_or_create_by(name: 'Shoes') do |cat|
    cat.description = 'All footwear'
    cat.sort_order = 2
  end
  
  accessories = Category.find_or_create_by(name: 'Accessories') do |cat|
    cat.description = 'Fashion accessories and add-ons'
    cat.sort_order = 3
  end
  
  jewelry = Category.find_or_create_by(name: 'Jewelry') do |cat|
    cat.description = 'All jewelry and watches'
    cat.sort_order = 4
  end
  
  # Clothing Subcategories
  clothing_subs = [
    { name: 'Tops', subcategories: ['T-Shirts', 'Blouses', 'Sweaters', 'Hoodies', 'Tank Tops'] },
    { name: 'Bottoms', subcategories: ['Jeans', 'Pants', 'Shorts', 'Skirts', 'Leggings'] },
    { name: 'Dresses', subcategories: ['Casual Dresses', 'Formal Dresses', 'Cocktail Dresses'] },
    { name: 'Outerwear', subcategories: ['Jackets', 'Coats', 'Blazers', 'Cardigans'] },
    { name: 'Undergarments', subcategories: ['Bras', 'Underwear', 'Shapewear', 'Sleepwear'] }
  ]
  
  # Shoes Subcategories
  shoe_subs = [
    { name: 'Athletic', subcategories: ['Sneakers', 'Running Shoes', 'Training Shoes'] },
    { name: 'Dress Shoes', subcategories: ['Heels', 'Pumps', 'Dress Flats', 'Oxfords'] },
    { name: 'Casual', subcategories: ['Loafers', 'Sandals', 'Slip-ons', 'Canvas Shoes'] },
    { name: 'Boots', subcategories: ['Ankle Boots', 'Knee-high Boots', 'Combat Boots'] }
  ]
  
  # Accessories Subcategories
  accessory_subs = [
    { name: 'Bags', subcategories: ['Handbags', 'Backpacks', 'Totes', 'Clutches'] },
    { name: 'Belts', subcategories: ['Leather Belts', 'Chain Belts', 'Fabric Belts'] },
    { name: 'Hats', subcategories: ['Baseball Caps', 'Beanies', 'Sun Hats', 'Fedoras'] },
    { name: 'Scarves', subcategories: ['Silk Scarves', 'Wool Scarves', 'Infinity Scarves'] },
    { name: 'Sunglasses', subcategories: ['Aviators', 'Wayfarers', 'Cat Eye', 'Oversized'] }
  ]
  
  # Jewelry Subcategories
  jewelry_subs = [
    { name: 'Necklaces', subcategories: ['Pendants', 'Necklace Chains', 'Chokers', 'Statement Necklaces'] },
    { name: 'Rings', subcategories: ['Wedding Rings', 'Fashion Rings', 'Cocktail Rings'] },
    { name: 'Earrings', subcategories: ['Studs', 'Hoops', 'Dangles', 'Ear Cuffs'] },
    { name: 'Bracelets', subcategories: ['Bangles', 'Bracelet Chains', 'Cuffs', 'Charm Bracelets'] },
    { name: 'Watches', subcategories: ['Digital Watches', 'Analog Watches', 'Smart Watches'] }
  ]
  
  # Create subcategories for each root category
  create_subcategories(clothing, clothing_subs)
  create_subcategories(shoes, shoe_subs)
  create_subcategories(accessories, accessory_subs)
  create_subcategories(jewelry, jewelry_subs)
end

def create_subcategories(parent, subcategory_data)
  subcategory_data.each_with_index do |sub_data, index|
    parent_cat = Category.find_or_create_by(name: sub_data[:name], parent_id: parent.id) do |cat|
      cat.description = "#{sub_data[:name]} #{parent.name.downcase}"
      cat.sort_order = index + 1
    end
    
    sub_data[:subcategories].each_with_index do |sub_name, sub_index|
      Category.find_or_create_by(name: sub_name, parent_id: parent_cat.id) do |cat|
        cat.description = "#{sub_name} #{parent_cat.name.downcase}"
        cat.sort_order = sub_index + 1
      end
    end
  end
end

# Create the taxonomy
create_category_taxonomy

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
