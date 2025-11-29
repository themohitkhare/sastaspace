require "test_helper"

class QuotaServiceTest < ActiveSupport::TestCase
  def setup
    @free_user = create(:user, plan_type: "free")
    @premium_user = create(:user, plan_type: "premium")
  end

  test "free user has inventory limit of 50" do
    limit = QuotaService.limit_for(@free_user, :inventory_items)
    assert_equal 50, limit
  end

  test "premium user has unlimited inventory" do
    limit = QuotaService.limit_for(@premium_user, :inventory_items)
    assert_equal Float::INFINITY, limit
  end

  test "free user has outfit limit of 10" do
    limit = QuotaService.limit_for(@free_user, :outfits)
    assert_equal 10, limit
  end

  test "free user has AI critique limit of 3 per day" do
    limit = QuotaService.limit_for(@free_user, :ai_critiques)
    assert_equal 3, limit
  end

  test "quota check passes when under limit" do
    # Create 49 items (under limit of 50)
    49.times { create(:inventory_item, user: @free_user) }

    assert_nothing_raised do
      QuotaService.check!(@free_user, :inventory_items)
    end
  end

  test "quota check fails when at limit" do
    # Create exactly 50 items
    50.times { create(:inventory_item, user: @free_user) }

    assert_raises(QuotaService::QuotaExceededError) do
      QuotaService.check!(@free_user, :inventory_items)
    end
  end

  test "quota check fails when over limit" do
    # Create 51 items (over limit)
    51.times { create(:inventory_item, user: @free_user) }

    assert_raises(QuotaService::QuotaExceededError) do
      QuotaService.check!(@free_user, :inventory_items)
    end
  end

  test "premium user never hits quota limit" do
    # Create 100 items (would exceed free limit)
    100.times { create(:inventory_item, user: @premium_user) }

    assert_nothing_raised do
      QuotaService.check!(@premium_user, :inventory_items)
    end
  end

  test "count_for returns correct inventory count" do
    create(:inventory_item, user: @free_user)
    create(:inventory_item, user: @free_user)

    count = QuotaService.count_for(@free_user, :inventory_items)
    assert_equal 2, count
  end

  test "count_for returns correct outfit count" do
    create(:outfit, user: @free_user)
    create(:outfit, user: @free_user)
    create(:outfit, user: @free_user)

    count = QuotaService.count_for(@free_user, :outfits)
    assert_equal 3, count
  end

  test "count_for returns daily AI critique count" do
    outfit = create(:outfit, user: @free_user)

    # Create critiques today
    AiAnalysis.create!(
      outfit: outfit,
      user: @free_user,
      analysis_type: "outfit_critique",
      analysis_data: { score: 85 },
      confidence_score: 0.85,
      created_at: Time.current
    )
    AiAnalysis.create!(
      outfit: outfit,
      user: @free_user,
      analysis_type: "outfit_critique",
      analysis_data: { score: 90 },
      confidence_score: 0.90,
      created_at: Time.current
    )

    # Create critique yesterday (should not count)
    AiAnalysis.create!(
      outfit: outfit,
      user: @free_user,
      analysis_type: "outfit_critique",
      analysis_data: { score: 80 },
      confidence_score: 0.80,
      created_at: 1.day.ago
    )

    count = QuotaService.count_for(@free_user, :ai_critiques)
    assert_equal 2, count
  end

  test "quota check for AI critiques respects daily limit" do
    outfit = create(:outfit, user: @free_user)

    # Create 3 critiques today (at limit)
    3.times do
      AiAnalysis.create!(
        outfit: outfit,
        user: @free_user,
        analysis_type: "outfit_critique",
        analysis_data: { score: 85 },
        confidence_score: 0.85,
        created_at: Time.current
      )
    end

    assert_raises(QuotaService::QuotaExceededError) do
      QuotaService.check!(@free_user, :ai_critiques)
    end
  end

  test "quota error message is user-friendly" do
    50.times { create(:inventory_item, user: @free_user) }

    error = assert_raises(QuotaService::QuotaExceededError) do
      QuotaService.check!(@free_user, :inventory_items)
    end

    assert_match(/limit of 50/, error.message)
    assert_match(/Upgrade to Premium/, error.message)
  end

  test "default plan_type is free" do
    # User factory should set plan_type to "free" by default
    user = create(:user)

    limit = QuotaService.limit_for(user, :inventory_items)
    assert_equal 50, limit
  end
end
