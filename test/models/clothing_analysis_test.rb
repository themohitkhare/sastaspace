require "test_helper"

class ClothingAnalysisTest < ActiveSupport::TestCase
  setup do
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
  end

  test "can create clothing_analysis" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {
        "total_items_detected" => 3,
        "people_count" => 1,
        "items" => [
          { "id" => "item_001", "item_name" => "Blue Shirt", "confidence" => 0.9 },
          { "id" => "item_002", "item_name" => "Black Jeans", "confidence" => 0.85 },
          { "id" => "item_003", "item_name" => "White Sneakers", "confidence" => 0.8 }
        ]
      },
      items_detected: 3,
      confidence: 0.85,
      status: "completed"
    )

    assert_not_nil analysis.id
    assert_equal @user, analysis.user
    assert_equal @image_blob.id, analysis.image_blob_id
    assert_equal 3, analysis.items_detected
    assert_equal "completed", analysis.status
  end

  test "belongs to user" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed"
    )

    assert_equal @user, analysis.user
    assert_equal analysis.user_id, @user.id
  end

  test "requires image_blob_id" do
    analysis = ClothingAnalysis.new(
      user: @user,
      parsed_data: {},
      items_detected: 0,
      status: "completed"
    )

    assert_not analysis.valid?
    assert_includes analysis.errors.full_messages, "Image blob can't be blank"
  end

  test "status has default value" do
    analysis = ClothingAnalysis.new(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0
    )

    # Status has a default value from enum, so it should be valid
    assert_equal "completed", analysis.status
    assert analysis.valid?
  end

  test "validates items_detected is non-negative" do
    analysis = ClothingAnalysis.new(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: -1,
      status: "completed"
    )

    assert_not analysis.valid?
    assert_includes analysis.errors.full_messages, "Items detected must be greater than or equal to 0"
  end

  test "validates confidence is between 0 and 1" do
    analysis = ClothingAnalysis.new(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      confidence: 1.5,
      status: "completed"
    )

    assert_not analysis.valid?
    assert_includes analysis.errors.full_messages, "Confidence must be in 0.0..1.0"
  end

  test "parsed_data_hash returns hash" do
    parsed_data = {
      "total_items_detected" => 2,
      "items" => [ { "id" => "item_001" } ]
    }
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: parsed_data,
      items_detected: 2,
      status: "completed"
    )

    assert_equal parsed_data, analysis.parsed_data_hash
  end

  test "total_items_detected returns value from parsed_data" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: { "total_items_detected" => 5 },
      items_detected: 3,
      status: "completed"
    )

    assert_equal 5, analysis.total_items_detected
  end

  test "total_items_detected falls back to items_detected" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 3,
      status: "completed"
    )

    assert_equal 3, analysis.total_items_detected
  end

  test "people_count returns value from parsed_data" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: { "people_count" => 2 },
      items_detected: 0,
      status: "completed"
    )

    assert_equal 2, analysis.people_count
  end

  test "items returns array from parsed_data" do
    items = [
      { "id" => "item_001", "item_name" => "Shirt" },
      { "id" => "item_002", "item_name" => "Pants" }
    ]
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: { "items" => items },
      items_detected: 2,
      status: "completed"
    )

    assert_equal items, analysis.items
  end

  test "image_blob returns ActiveStorage blob" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed"
    )

    assert_equal @image_blob, analysis.image_blob
  end

  test "calculate_average_confidence calculates from items" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {
        "items" => [
          { "confidence" => 0.9 },
          { "confidence" => 0.8 },
          { "confidence" => 0.7 }
        ]
      },
      items_detected: 3,
      confidence: 0.85,
      status: "completed"
    )

    avg = analysis.calculate_average_confidence
    assert_equal 0.8, avg # (0.9 + 0.8 + 0.7) / 3 = 0.8
  end

  test "calculate_average_confidence falls back to stored confidence" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: { "items" => [] },
      items_detected: 0,
      confidence: 0.75,
      status: "completed"
    )

    assert_equal 0.75, analysis.calculate_average_confidence
  end

  test "has_many inventory_items" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed"
    )

    category = create(:category, :clothing)
    item1 = create(:inventory_item, user: @user, category: category, clothing_analysis: analysis)
    item2 = create(:inventory_item, user: @user, category: category, clothing_analysis: analysis)

    assert_equal 2, analysis.inventory_items.count
    assert_includes analysis.inventory_items, item1
    assert_includes analysis.inventory_items, item2
  end

  test "recent scope orders by created_at desc" do
    analysis1 = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed",
      created_at: 2.days.ago
    )

    analysis2 = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed",
      created_at: 1.day.ago
    )

    recent = ClothingAnalysis.recent.limit(2)
    assert_equal analysis2.id, recent.first.id
    assert_equal analysis1.id, recent.second.id
  end

  test "high_confidence scope filters by confidence" do
    high_analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      confidence: 0.8,
      status: "completed"
    )

    low_analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      confidence: 0.5,
      status: "completed"
    )

    high_confidence_analyses = ClothingAnalysis.high_confidence
    assert_includes high_confidence_analyses, high_analysis
    assert_not_includes high_confidence_analyses, low_analysis
  end

  test "with_items scope filters by items_detected" do
    with_items = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 3,
      status: "completed"
    )

    without_items = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "completed"
    )

    with_items_analyses = ClothingAnalysis.with_items
    assert_includes with_items_analyses, with_items
    assert_not_includes with_items_analyses, without_items
  end

  test "status enum works correctly" do
    analysis = ClothingAnalysis.create!(
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {},
      items_detected: 0,
      status: "pending"
    )

    assert analysis.pending?
    assert_not analysis.completed?

    analysis.completed!
    assert analysis.completed?
    assert_not analysis.pending?
  end
end
