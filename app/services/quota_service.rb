class QuotaService
  LIMITS = {
    free: {
      inventory_items: 50,
      outfits: 10,
      ai_critiques: 3 # per day
    },
    premium: {
      inventory_items: Float::INFINITY,
      outfits: Float::INFINITY,
      ai_critiques: Float::INFINITY
    }
  }.freeze

  class QuotaExceededError < StandardError; end

  def self.check!(user, resource)
    new(user).check!(resource)
  end

  def self.limit_for(user, resource)
    new(user).limit_for(resource)
  end

  def self.count_for(user, resource)
    new(user).count_for(resource)
  end

  def initialize(user)
    @user = user
    @plan = (user.plan_type || "free").to_sym
  end

  def check!(resource)
    limit = limit_for(resource)
    return if limit == Float::INFINITY

    count = count_for(resource)

    if count >= limit
      raise QuotaExceededError, "You have reached the limit of #{limit} for #{resource.to_s.humanize.downcase}. Upgrade to Premium for unlimited access."
    end
  end

  def limit_for(resource)
    LIMITS[@plan][resource] || 0
  end

  def count_for(resource)
    case resource
    when :inventory_items
      @user.inventory_items.count
    when :outfits
      @user.outfits.count
    when :ai_critiques
      # Daily limit - count critiques for user's outfits
      AiAnalysis.where(
        outfit_id: @user.outfits.select(:id),
        analysis_type: "outfit_critique",
        created_at: Time.zone.now.beginning_of_day..Time.zone.now.end_of_day
      ).count
    else
      0
    end
  end
end
