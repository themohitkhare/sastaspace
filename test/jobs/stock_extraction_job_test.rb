require "test_helper"

class StockExtractionJobTest < ActiveJob::TestCase
  setup do
    @user = create(:user)
    @image_blob = ActiveStorage::Blob.create_and_upload!(
      io: File.open(Rails.root.join("test/fixtures/files/sample_image.jpg")),
      filename: "sample_image.jpg",
      content_type: "image/jpeg"
    )
    @analysis = create(:clothing_analysis,
      user: @user,
      image_blob_id: @image_blob.id,
      parsed_data: {
        "items" => [
          { "id" => "item_001", "item_name" => "Blue Shirt" },
          { "id" => "item_002", "item_name" => "Black Jeans" },
          { "id" => "item_003", "item_name" => "White Sneakers" }
        ]
      }
    )
  end

  test "job queues correctly" do
    assert_enqueued_with(job: StockExtractionJob, args: [ @analysis.id, [ "item_001", "item_002" ] ]) do
      StockExtractionJob.perform_later(@analysis.id, [ "item_001", "item_002" ])
    end
  end

  test "job processes selected items and creates extraction results" do
    ActionCable.server.stubs(:broadcast)

    assert_difference "ExtractionResult.count", 2 do
      StockExtractionJob.perform_now(@analysis.id, [ "item_001", "item_002" ])
    end

    results = ExtractionResult.where(clothing_analysis: @analysis)
    assert_equal 2, results.count
    assert results.all? { |r| r.status == "completed" }
  end

  test "job broadcasts progress updates" do
    # Capture all broadcasts
    broadcasts = []
    ActionCable.server.stubs(:broadcast).with { |channel, message| broadcasts << { channel: channel, message: message }; true }

    StockExtractionJob.perform_now(@analysis.id, [ "item_001", "item_002" ])

    # Verify progress broadcasts
    progress_broadcasts = broadcasts.select { |b| b[:message][:type] == "extraction_progress" }
    assert progress_broadcasts.count >= 2, "Expected at least 2 progress broadcasts, got #{progress_broadcasts.count}"
  end

  test "job broadcasts item completion" do
    # Allow progress broadcasts as well
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_progress")
    )
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "item_extraction_complete", item_id: "item_001")
    ).at_least_once
    # Allow extraction_complete broadcast (job completes after processing items)
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_complete")
    )

    StockExtractionJob.perform_now(@analysis.id, [ "item_001" ])
  end

  test "job broadcasts overall completion" do
    # Allow progress and item completion broadcasts
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_progress")
    )
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "item_extraction_complete")
    )
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_complete", total_items: 2)
    ).at_least_once

    StockExtractionJob.perform_now(@analysis.id, [ "item_001", "item_002" ])
  end

  test "job handles empty selected items" do
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_failed")
    ).at_least_once

    assert_no_difference "ExtractionResult.count" do
      StockExtractionJob.perform_now(@analysis.id, [])
    end
  end

  test "job handles invalid item IDs" do
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_failed")
    ).at_least_once

    assert_no_difference "ExtractionResult.count" do
      StockExtractionJob.perform_now(@analysis.id, [ "invalid_id" ])
    end
  end

  test "job handles extraction errors gracefully" do
    # Stub extract_single_item to raise an error
    job = StockExtractionJob.new
    job.stubs(:extract_single_item).raises(StandardError.new("Extraction failed"))

    # Allow progress broadcasts
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_progress")
    )
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "item_extraction_failed")
    ).at_least_once
    # Allow extraction_complete broadcast (job completes even with failed items)
    ActionCable.server.stubs(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_entries(type: "extraction_complete")
    )

    # Should create a failed extraction result
    assert_difference "ExtractionResult.count", 1 do
      job.perform(@analysis.id, [ "item_001" ])
    end

    result = ExtractionResult.last
    assert_equal "failed", result.status
  end

  test "job handles RecordNotFound errors" do
    # Job has discard_on RecordNotFound, which applies even in tests
    # So the exception will be caught and discarded, broadcasting before it does
    ActionCable.server.expects(:broadcast).with(
      "extraction_99999",
      has_entries(type: "extraction_failed")
    ).at_least_once

    # With discard_on, the error is caught and not re-raised in tests
    assert_no_difference "ExtractionResult.count" do
      StockExtractionJob.perform_now(99999, [ "item_001" ])
    end
  end

  test "job broadcasts extraction failed on general errors" do
    # Force an error by making analysis.items return nil
    # Need to use any_instance since the job creates a new instance
    ClothingAnalysis.any_instance.stubs(:items).returns(nil)

    # Collect broadcasts to verify failure notification
    broadcasts = []
    ActionCable.server.stubs(:broadcast).with { |channel, data| broadcasts << data; true }

    # The job should fail early and not create any extraction results
    assert_no_difference "ExtractionResult.count" do
      StockExtractionJob.perform_now(@analysis.id, [ "item_001" ])
    end

    # Verify failure was broadcast (use string keys, not symbols)
    assert broadcasts.any? { |b| b[:type] == "extraction_failed" || b["type"] == "extraction_failed" },
      "Should broadcast extraction_failed. Broadcasts: #{broadcasts.inspect}"
  end

  test "job processes items in correct order" do
    ActionCable.server.stubs(:broadcast)

    StockExtractionJob.perform_now(@analysis.id, [ "item_001", "item_002", "item_003" ])

    results = ExtractionResult.where(clothing_analysis: @analysis).order(:created_at)
    assert_equal 3, results.count

    # Verify item_data matches the order
    assert_equal "item_001", results[0].item_id
    assert_equal "item_002", results[1].item_id
    assert_equal "item_003", results[2].item_id
  end

  test "job calculates progress percentage correctly" do
    # Collect broadcasts to verify progress updates
    broadcasts = []
    ActionCable.server.stubs(:broadcast).with { |channel, data| broadcasts << data; true }

    StockExtractionJob.perform_now(@analysis.id, [ "item_001", "item_002" ])

    # Verify progress broadcasts were sent (use string keys, not symbols)
    progress_broadcasts = broadcasts.select { |b| b[:type] == "extraction_progress" || b["type"] == "extraction_progress" }
    assert progress_broadcasts.any? { |b| (b[:progress_percent] || b["progress_percent"]) == 50 },
      "Should broadcast 50% progress. Progress broadcasts: #{progress_broadcasts.inspect}"
    assert progress_broadcasts.any? { |b| (b[:progress_percent] || b["progress_percent"]) == 100 },
      "Should broadcast 100% progress. Progress broadcasts: #{progress_broadcasts.inspect}"
  end

  test "job includes job_id in broadcasts" do
    ActionCable.server.expects(:broadcast).with(
      "extraction_#{@analysis.id}",
      has_key(:job_id)
    ).at_least_once

    StockExtractionJob.perform_now(@analysis.id, [ "item_001" ])
  end
end
