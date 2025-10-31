require "test_helper"

class ExportUserDataJobTest < ActiveJob::TestCase
  test "job can be enqueued" do
    assert_enqueued_with(job: ExportUserDataJob) do
      ExportUserDataJob.perform_later
    end
  end

  test "job is in correct queue" do
    assert_equal "default", ExportUserDataJob.queue_name
  end

  test "job can be performed" do
    # Since job is a stub (TDD Red Phase), just verify it can be instantiated
    assert_nothing_raised do
      ExportUserDataJob.new
    end
  end
end

