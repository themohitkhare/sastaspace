require "test_helper"

module Maintenance
  class BackfillEmbeddingsTaskTest < ActiveSupport::TestCase
    def setup
      @user = create(:user)
      @category = create(:category, name: "Test Category #{SecureRandom.hex(4)}")

      # Create items without embeddings
      @item1 = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
      @item2 = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
      @item3 = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
    end

    test "collection returns items without embeddings" do
      task = Maintenance::BackfillEmbeddingsTask.new
      collection = task.collection

      assert_kind_of ActiveRecord::Relation, collection
      assert_includes collection.to_sql, "embedding_vector"
      assert_includes collection.to_sql, "IS NULL"
    end

    test "count returns collection count" do
      task = Maintenance::BackfillEmbeddingsTask.new
      count = task.count

      assert_kind_of Integer, count
      assert count >= 3, "Should include our test items"
    end

    test "process generates embedding for item" do
      task = Maintenance::BackfillEmbeddingsTask.new
      mock_vector = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

      EmbeddingService.expects(:generate_for_item).with(@item1).returns(mock_vector)

      task.process(@item1)

      @item1.reload
      assert @item1.embedding_vector.present?
      assert_equal 1, task.job_results[:processed].count
      assert_equal 0, task.job_results[:failed].count
      assert_equal 0, task.job_results[:skipped].count
    end

    test "process skips item when EmbeddingService returns nil" do
      task = Maintenance::BackfillEmbeddingsTask.new

      EmbeddingService.expects(:generate_for_item).with(@item1).returns(nil)

      task.process(@item1)

      @item1.reload
      assert_nil @item1.embedding_vector
      assert_equal 0, task.job_results[:processed].count
      assert_equal 1, task.job_results[:skipped].count
      assert_equal "EmbeddingService returned nil", task.job_results[:skipped].first[:reason]
    end

    test "process handles errors gracefully" do
      task = Maintenance::BackfillEmbeddingsTask.new

      EmbeddingService.expects(:generate_for_item).with(@item1).raises(StandardError, "Embedding failed")

      task.process(@item1)

      @item1.reload
      assert_nil @item1.embedding_vector
      assert_equal 0, task.job_results[:processed].count
      assert_equal 1, task.job_results[:failed].count
      assert_equal "Embedding failed", task.job_results[:failed].first[:error_message]
    end

    test "after_task logs summary" do
      task = Maintenance::BackfillEmbeddingsTask.new
      mock_vector = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

      # Process one item successfully
      EmbeddingService.expects(:generate_for_item).with(@item1).returns(mock_vector)
      task.process(@item1)

      # Skip one item
      EmbeddingService.expects(:generate_for_item).with(@item2).returns(nil)
      task.process(@item2)

      # Fail one item
      EmbeddingService.expects(:generate_for_item).with(@item3).raises(StandardError, "Error")
      task.process(@item3)

      # Capture log output
      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/BackfillEmbeddings.*Task completed/, log_content)
      assert_match(/processed.*1/, log_content)
      assert_match(/failed.*1/, log_content)
      assert_match(/skipped.*1/, log_content)
    ensure
      Rails.logger = original_logger
    end

    test "after_task logs failed items details" do
      task = Maintenance::BackfillEmbeddingsTask.new

      EmbeddingService.expects(:generate_for_item).with(@item1).raises(StandardError, "Error 1")
      task.process(@item1)

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/Failed items/, log_content)
      assert_match(/Item #{@item1.id}/, log_content)
      assert_match(/Error 1/, log_content)
    ensure
      Rails.logger = original_logger
    end

    test "after_task logs processed items" do
      task = Maintenance::BackfillEmbeddingsTask.new
      mock_vector = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

      EmbeddingService.expects(:generate_for_item).with(@item1).returns(mock_vector)
      task.process(@item1)

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/Successfully processed/, log_content)
      assert_match(/Item #{@item1.id}/, log_content)
    ensure
      Rails.logger = original_logger
    end

    test "after_task logs skipped items" do
      task = Maintenance::BackfillEmbeddingsTask.new

      EmbeddingService.expects(:generate_for_item).with(@item1).returns(nil)
      task.process(@item1)

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/Skipped.*items/, log_content)
      assert_match(/Item #{@item1.id}/, log_content)
      assert_match(/EmbeddingService returned nil/, log_content)
    ensure
      Rails.logger = original_logger
    end

    test "after_task truncates long failure lists" do
      task = Maintenance::BackfillEmbeddingsTask.new

      # Create 25 failures
      25.times do |i|
        item = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
        EmbeddingService.expects(:generate_for_item).with(item).raises(StandardError, "Error #{i}")
        task.process(item)
      end

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/... and 5 more/, log_content) # Should show first 20, then "... and 5 more"
    ensure
      Rails.logger = original_logger
    end

    test "after_task truncates long processed lists" do
      task = Maintenance::BackfillEmbeddingsTask.new
      mock_vector = Array.new(EmbeddingService::EXPECTED_DIMENSIONS) { rand(-1.0..1.0) }

      # Create 15 processed items
      15.times do |i|
        item = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
        EmbeddingService.expects(:generate_for_item).with(item).returns(mock_vector)
        task.process(item)
      end

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/... and 5 more/, log_content) # Should show first 10, then "... and 5 more"
    ensure
      Rails.logger = original_logger
    end

    test "after_task truncates long skipped lists" do
      task = Maintenance::BackfillEmbeddingsTask.new

      # Create 15 skipped items
      15.times do |i|
        item = create(:inventory_item, user: @user, category: @category, embedding_vector: nil)
        EmbeddingService.expects(:generate_for_item).with(item).returns(nil)
        task.process(item)
      end

      log_output = StringIO.new
      original_logger = Rails.logger
      Rails.logger = Logger.new(log_output)

      task.after_task

      log_content = log_output.string
      assert_match(/... and 5 more/, log_content) # Should show first 10, then "... and 5 more"
    ensure
      Rails.logger = original_logger
    end

    test "initialize sets up job_results hash" do
      # MaintenanceTasks::Task might require arguments, so we'll test through process
      task = Maintenance::BackfillEmbeddingsTask.new

      # The job_results should be initialized
      assert task.job_results.is_a?(Hash)
      assert task.job_results.key?(:processed)
      assert task.job_results.key?(:failed)
      assert task.job_results.key?(:skipped)
      assert task.job_results[:processed].is_a?(Array)
      assert task.job_results[:failed].is_a?(Array)
      assert task.job_results[:skipped].is_a?(Array)
    end
  end
end
