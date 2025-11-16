# Custom test tasks
namespace :test do
  desc "Run all tests with full output (shows PASS, FAIL, and ERROR)"
  task :full do
    # Set environment variable BEFORE loading test environment
    ENV["SHOW_ALL_TESTS"] = "1"
    ENV["TEST_FULL"] = "1"

    # Load environment after setting ENV vars
    Rake::Task["test"].invoke
  end

  desc "Run all tests with filtered output (shows only FAIL and ERROR) - default behavior"
  task :filtered do
    ENV.delete("SHOW_ALL_TESTS")
    ENV.delete("TEST_FULL")
    Rake::Task["test"].invoke
  end

  namespace :system do
    desc "Run system tests with full output (shows PASS, FAIL, and ERROR)"
    task :full do
      # Set environment variable BEFORE loading test environment
      ENV["SHOW_ALL_TESTS"] = "1"
      ENV["TEST_FULL"] = "1"

      # Run system tests
      Rake::Task["test:system"].invoke
    end

    desc "Run system tests with filtered output (shows only FAIL and ERROR) - default behavior"
    task :filtered do
      ENV.delete("SHOW_ALL_TESTS")
      ENV.delete("TEST_FULL")
      Rake::Task["test:system"].invoke
    end
  end
end
