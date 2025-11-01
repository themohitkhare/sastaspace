class ColorCoordinationService
  # Analyze color coordination for an outfit (array of inventory items)
  # Returns a score and feedback
  def self.analyze(outfit_items)
    items = Array(outfit_items)
    return default_response if items.empty?

    # Extract colors from items
    item_colors = extract_colors_from_items(items)
    return default_response if item_colors.empty?

    # Analyze coordination
    analysis = {
      score: calculate_coordination_score(item_colors),
      colors: item_colors,
      feedback: generate_feedback(item_colors),
      warnings: identify_warnings(item_colors),
      suggestions: generate_suggestions(item_colors)
    }

    analysis
  end

  private

  def self.extract_colors_from_items(items)
    colors_map = {}

    items.each do |item|
      # Try to get color from metadata
      # Handle metadata as hash or JSON string
      metadata_hash = if item.metadata.is_a?(Hash)
                       item.metadata
      elsif item.metadata.is_a?(String)
                       JSON.parse(item.metadata) rescue {}
      else
                       {}
      end

      color_str = metadata_hash["color"] || item.color

      # Fallback to AI analysis
      if color_str.blank?
        latest_analysis = item.ai_analyses.order(created_at: :desc).first
        if latest_analysis
          analysis_colors = latest_analysis.analysis_data_hash["colors"] || []
          color_str = analysis_colors.first if analysis_colors.any?
        end
      end

      # Extract and normalize colors
      if color_str.present?
        normalized_colors = normalize_colors(color_str)
        normalized_colors.each do |color|
          colors_map[color] ||= []
          colors_map[color] << item.id
        end
      end
    end

    colors_map
  end

  def self.normalize_colors(color_string)
    return [] unless color_string.present?

    # Normalize color string to lowercase
    color_lower = color_string.to_s.downcase.strip

    # Map common color variations to standard colors
    color_map = {
      "navy" => "blue",
      "light blue" => "blue",
      "dark blue" => "blue",
      "royal blue" => "blue",
      "sky blue" => "blue",
      "grey" => "gray",
      "charcoal" => "gray",
      "dark gray" => "gray",
      "light gray" => "gray",
      "beige" => "tan",
      "khaki" => "tan",
      "maroon" => "red",
      "burgundy" => "red",
      "crimson" => "red",
      "salmon" => "pink",
      "rose" => "pink",
      "lavender" => "purple",
      "violet" => "purple",
      "indigo" => "purple",
      "olive" => "green",
      "emerald" => "green",
      "lime" => "green",
      "amber" => "orange",
      "coral" => "orange",
      "champagne" => "yellow",
      "cream" => "white",
      "ivory" => "white",
      "off-white" => "white",
      "ebony" => "black"
    }

    # Check if the color matches any mapped variation
    mapped_color = color_map[color_lower]
    return [ mapped_color ] if mapped_color

    # Extract base colors from color string (handles "red and blue", "blue/white", etc.)
    base_colors = %w[red blue green yellow orange purple pink brown black white gray tan]
    found_colors = base_colors.select { |base| color_lower.include?(base) }

    found_colors.empty? ? [ color_lower ] : found_colors
  end

  def self.calculate_coordination_score(color_map)
    unique_colors = color_map.keys.length
    return 0.5 if unique_colors == 0
    return 1.0 if unique_colors == 1 # Monochromatic can be good

    # Check for color harmony
    harmony_score = check_color_harmony(color_map.keys)

    # Check for neutral base (black, white, gray, tan)
    has_neutral = color_map.keys.any? { |c| %w[black white gray tan].include?(c) }
    neutral_bonus = has_neutral ? 0.2 : 0.0

    # Check for complementary colors
    complement_score = check_complementary_colors(color_map.keys)

    # Check for too many colors (over 4 unique colors usually looks busy)
    diversity_penalty = unique_colors > 4 ? -0.2 : 0.0

    base_score = 0.6
    total_score = base_score + harmony_score + neutral_bonus + complement_score + diversity_penalty

    # Clamp between 0 and 1
    [ 0.0, [ 1.0, total_score ].min ].max
  end

  def self.check_color_harmony(colors)
    return 0.0 if colors.length < 2

    # Color harmony rules
    harmonies = {
      "analogous" => [
        %w[red orange yellow],
        %w[yellow green blue],
        %w[blue purple pink],
        %w[pink red orange]
      ],
      "triadic" => [
        %w[red yellow blue],
        %w[orange green purple]
      ],
      "complementary" => [
        %w[red green],
        %w[blue orange],
        %w[yellow purple]
      ]
    }

    harmonies.each do |harmony_type, color_groups|
      color_groups.each do |group|
        if (colors & group).length >= 2
          return 0.3 if harmony_type == "analogous"
          return 0.4 if harmony_type == "triadic"
          return 0.3 if harmony_type == "complementary"
        end
      end
    end

    0.0
  end

  def self.check_complementary_colors(colors)
    complements = [
      %w[red green],
      %w[blue orange],
      %w[yellow purple]
    ]

    complements.each do |pair|
      if (colors & pair).length == 2
        return 0.2 # Strong complementary pair
      end
    end

    0.0
  end

  def self.generate_feedback(color_map)
    unique_colors = color_map.keys.length

    if unique_colors == 1
      "Monochromatic look - elegant and cohesive!"
    elsif unique_colors == 2
      "Simple two-color palette - clean and balanced."
    elsif unique_colors == 3
      "Three-color combination - well-balanced."
    elsif unique_colors == 4
      "Multi-color outfit - bold and expressive."
    else
      "Many colors detected - consider simplifying for better cohesion."
    end
  end

  def self.identify_warnings(color_map)
    warnings = []
    unique_colors = color_map.keys.length

    # Too many colors
    if unique_colors > 5
      warnings << "Too many colors (#{unique_colors}) - may look busy. Consider a neutral base."
    end

    # Clashing bright colors
    bright_colors = color_map.keys & %w[red orange yellow bright_pink]
    if bright_colors.length > 2
      warnings << "Multiple bright colors may clash. Try pairing with neutrals."
    end

    # Check for clashing combinations
    clashing_pairs = [
      %w[red green], # When both are bright
      %w[orange blue] # When both are bright
    ]

    clashing_pairs.each do |pair|
      if (color_map.keys & pair).length == 2
        # Check if they're bright (simplified - in real app, check saturation)
        warnings << "Consider softening #{pair.join(' and ')} combination or adding a neutral."
      end
    end

    warnings
  end

  def self.generate_suggestions(color_map)
    suggestions = []
    unique_colors = color_map.keys.length

    # If no neutrals, suggest adding one
    has_neutral = color_map.keys.any? { |c| %w[black white gray tan].include?(c) }
    unless has_neutral
      suggestions << "Add a neutral color (black, white, gray, or tan) to anchor the outfit."
    end

    # If too many colors, suggest reducing
    if unique_colors > 4
      suggestions << "Consider reducing to 2-3 main colors for a more cohesive look."
    end

    # If single color, suggest accent
    if unique_colors == 1
      suggestions << "Add a complementary accent color to create visual interest."
    end

    suggestions
  end

  def self.default_response
    {
      score: 0.5,
      colors: {},
      feedback: "Add items to analyze color coordination",
      warnings: [],
      suggestions: []
    }
  end
end
