require "application_system_test_case"

class AdminMonitoringTest < ApplicationSystemTestCase
  def setup
    @user = create(:user, password: "Password123!")
    @admin_user = create(:user, password: "Password123!")

    # Set admin via SQL (only way it works due to readonly field)
    ActiveRecord::Base.connection.execute(
      "UPDATE users SET admin = true WHERE id = #{@admin_user.id}"
    )
    @admin_user.reload

    # Stub JobMonitoringService methods to return test data
    JobMonitoringService.stubs(:queue_health).returns({
      status: "healthy",
      queues: {
        "default" => {
          depth: 5,
          ready: 3,
          claimed: 2,
          scheduled: 0,
          blocked: 0,
          paused: false
        }
      },
      workers: {
        total: 2,
        active: 2,
        stale: 0,
        processes: [
          { name: "worker-1", pid: 12345, started_at: 1.hour.ago.iso8601 }
        ]
      },
      jobs: {
        completed: 100,
        average_processing_time_ms: 150.5,
        median_processing_time_ms: 120.0,
        p95_processing_time_ms: 300.0,
        p99_processing_time_ms: 500.0,
        time_window_seconds: 3600
      },
      failures: {
        total: 2,
        failure_rate: 0.02,
        failure_rate_percent: 2.0,
        by_job_class: {
          "TestJob" => 2
        },
        time_window_seconds: 3600
      },
      alerts: []
    })

    JobMonitoringService.stubs(:capacity_metrics).returns({
      queue_depths: {
        "default" => 5
      },
      worker_capacity: {
        total_workers: 2,
        active_workers: 2
      },
      processing_rate: {
        jobs_per_minute: 10,
        estimated_time_to_clear_minutes: 0.5
      }
    })

    JobMonitoringService.stubs(:job_metrics).returns({
      completed: 100,
      average_processing_time_ms: 150.5,
      median_processing_time_ms: 120.0,
      p95_processing_time_ms: 300.0,
      p99_processing_time_ms: 500.0,
      time_window_seconds: 3600
    })

    JobMonitoringService.stubs(:failure_metrics).returns({
      total: 2,
      failure_rate: 0.02,
      failure_rate_percent: 2.0,
      by_job_class: {
        "TestJob" => 2
      },
      time_window_seconds: 3600
    })

    JobMonitoringService.stubs(:job_class_metrics).returns({
      total: 10,
      completed: 8,
      failed: 2,
      success_rate: 80.0,
      average_processing_time_ms: 120.0,
      time_window_seconds: 3600
    })
  end

  test "admin link appears in navigation for admin users" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@admin_user.first_name}!", wait: 5

    # Check that Admin link is visible
    assert_selector "a", text: "Admin", wait: 5
  end

  test "admin link does not appear for non-admin users" do
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@user.first_name}!", wait: 5

    # Check that Admin link is NOT visible
    assert_no_selector "a", text: "Admin"
  end

  test "admin user can access dashboard from navigation" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@admin_user.first_name}!", wait: 5

    # Click Admin link
    click_link "Admin"

    # Should be on admin dashboard
    assert_selector "h1", text: "Admin Dashboard", wait: 5
    assert_text "Job Queue Health"
    assert_text "Healthy", wait: 5
  end

  test "non-admin user is redirected when accessing admin dashboard" do
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@user.first_name}!", wait: 5

    # Try to access admin dashboard directly
    visit "/admin/dashboard"

    # Should be redirected to root with error message
    assert_text "Access denied", wait: 5
  end

  test "admin user can navigate to job monitoring page" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@admin_user.first_name}!", wait: 5

    # Navigate to admin dashboard
    click_link "Admin"
    assert_selector "h1", text: "Admin Dashboard", wait: 5

    # Click Job Monitoring link
    click_link "Job Monitoring"

    # Should be on job monitoring page
    assert_selector "h1", text: "Job Monitoring", wait: 5
    assert_text "Queue Health"
  end

  test "admin user can navigate between admin pages" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Wait for login to complete
    assert_text "Hello, #{@admin_user.first_name}!", wait: 5

    # Navigate to admin dashboard
    click_link "Admin"
    assert_selector "h1", text: "Admin Dashboard", wait: 5

    # Navigate to Job Monitoring
    click_link "Job Monitoring"
    assert_selector "h1", text: "Job Monitoring", wait: 5

    # Navigate back to Dashboard
    click_link "Dashboard"
    assert_selector "h1", text: "Admin Dashboard", wait: 5
  end

  test "admin dashboard displays job queue health" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to admin dashboard
    click_link "Admin"

    # Check for health status
    assert_text "Status", wait: 5
    assert_text "Healthy", wait: 5
    assert_text "Active Workers"
    assert_text "2" # From stubbed data
    assert_text "Active Alerts"
  end

  test "admin dashboard displays capacity metrics" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to admin dashboard
    click_link "Admin"

    # Check for capacity planning section
    assert_text "Capacity Planning", wait: 5
    assert_text "Processing Rate"
    assert_text "jobs/minute"
  end

  test "job monitoring page displays queue metrics" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to admin dashboard then job monitoring
    click_link "Admin"
    click_link "Job Monitoring"

    # Check for queue metrics
    assert_text "Queue Health", wait: 5
    assert_text "default" # Queue name from stubbed data
    assert_text "Depth"
  end

  test "job monitoring page displays performance metrics" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to job monitoring
    click_link "Admin"
    click_link "Job Monitoring"

    # Check for performance metrics
    assert_text "Performance Metrics", wait: 5
    assert_text "Completed"
    assert_text "Avg Time"
  end

  test "job monitoring page displays failure metrics" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to job monitoring
    click_link "Admin"
    click_link "Job Monitoring"

    # Check for failure metrics
    assert_text "Failure Metrics", wait: 5
    assert_text "Total Failures"
    assert_text "Failure Rate"
  end

  test "admin user can access Mission Control dashboard" do
    visit "/login"
    fill_in "Email", with: @admin_user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Navigate to admin dashboard
    click_link "Admin"

    # Click Mission Control link
    click_link "Mission Control"

    # Should be on Mission Control page (it's a Rails engine)
    # The exact content depends on Mission Control, but we should be on the right path
    assert_current_path "/admin/jobs/monitor", wait: 5
  end

  test "non-admin user cannot access Mission Control" do
    visit "/login"
    fill_in "Email", with: @user.email
    fill_in "Password", with: "Password123!"
    click_button "Sign In"

    # Try to access Mission Control directly
    visit "/admin/jobs/monitor"

    # Should be redirected (Mission Control has its own auth)
    # The exact behavior depends on Mission Control's auth setup
    # But we should not see the Mission Control interface
    sleep 2 # Give it time to redirect
    # If redirected, we won't be on the monitor path
    assert_not_equal "/admin/jobs/monitor", page.current_path
  end

  test "unauthenticated user is redirected to login when accessing admin dashboard" do
    visit "/admin/dashboard"

    # Should be redirected to login
    assert_current_path "/login", wait: 5
  end
end
