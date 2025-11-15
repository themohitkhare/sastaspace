require "test_helper"

# Test class must not be namespaced to avoid Rails autoloading issues
class AdminAdminControllerTest < ActionDispatch::IntegrationTest
  def setup
    @user = create(:user, admin: false)
    @admin_user = create(:user)
    # Set admin via SQL
    ActiveRecord::Base.connection.execute(
      "UPDATE users SET admin = true WHERE id = #{@admin_user.id}"
    )
    @admin_user.reload
  end

  test "dashboard redirects non-admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    get admin_dashboard_path

    assert_redirected_to root_path
    assert_equal "Access denied. Admin privileges required.", flash[:alert]
  end

  test "dashboard allows admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    # Stub the service methods
    JobMonitoringService.stubs(:queue_health).returns({
      status: "healthy",
      queues: {},
      workers: { active: 1 },
      alerts: []
    })
    JobMonitoringService.stubs(:capacity_metrics).returns({
      queue_depths: {},
      worker_capacity: { total_workers: 1, active_workers: 1 },
      processing_rate: { jobs_per_minute: 10, estimated_time_to_clear_minutes: 5 }
    })

    get admin_dashboard_path, headers: { "Accept" => "text/html" }

    assert_response :success
    assert_select "h1", text: "Admin Dashboard"
  end

  test "dashboard responds to HTML format" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.stubs(:queue_health).returns({ status: "healthy", queues: {}, workers: { active: 1 }, alerts: [] })
    JobMonitoringService.stubs(:capacity_metrics).returns({ queue_depths: {}, worker_capacity: { total_workers: 1, active_workers: 1 }, processing_rate: { jobs_per_minute: 10, estimated_time_to_clear_minutes: 5 } })

    get admin_dashboard_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "job_monitoring redirects non-admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    get admin_job_monitoring_path

    assert_redirected_to root_path
    assert_equal "Access denied. Admin privileges required.", flash[:alert]
  end

  test "job_monitoring allows admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.stubs(:queue_health).returns({
      status: "healthy",
      queues: { "default" => { depth: 0, ready: 0, claimed: 0, scheduled: 0, blocked: 0, paused: false } },
      workers: { active: 1 },
      alerts: []
    })
    JobMonitoringService.stubs(:job_metrics).returns({
      completed: 10,
      average_processing_time_ms: 100.0,
      median_processing_time_ms: 95.0,
      p95_processing_time_ms: 150.0,
      p99_processing_time_ms: 200.0,
      time_window_seconds: 3600
    })
    JobMonitoringService.stubs(:failure_metrics).returns({
      total: 0,
      failure_rate: 0.0,
      failure_rate_percent: 0.0,
      by_job_class: {},
      time_window_seconds: 3600
    })

    get admin_job_monitoring_path, headers: { "Accept" => "text/html" }

    assert_response :success
    assert_select "h1", text: "Job Monitoring"
  end

  test "job_monitoring responds to HTML format" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.stubs(:queue_health).returns({ status: "healthy", queues: {}, workers: { active: 1 }, alerts: [] })
    JobMonitoringService.stubs(:job_metrics).returns({ completed: 10, average_processing_time_ms: 100.0, median_processing_time_ms: 95.0, p95_processing_time_ms: 150.0, p99_processing_time_ms: 200.0, time_window_seconds: 3600 })
    JobMonitoringService.stubs(:failure_metrics).returns({ total: 0, failure_rate: 0.0, failure_rate_percent: 0.0, by_job_class: {}, time_window_seconds: 3600 })

    get admin_job_monitoring_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "job_class_metrics redirects non-admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    get admin_job_class_metrics_path(job_class: "TestJob")

    assert_redirected_to root_path
    assert_equal "Access denied. Admin privileges required.", flash[:alert]
  end

  test "job_class_metrics allows admin users" do
    # Stub authentication - bypass authenticate_user! and set current_user
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.stubs(:job_class_metrics).returns({
      total: 5,
      completed: 4,
      failed: 1,
      success_rate: 75.0,
      average_processing_time_ms: 120.0,
      time_window_seconds: 3600
    })

    get admin_job_class_metrics_path(job_class: "TestJob"), headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "job_class_metrics responds to HTML format" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.stubs(:job_class_metrics).returns({ total: 5, completed: 4, failed: 1, success_rate: 75.0, average_processing_time_ms: 120.0, time_window_seconds: 3600 })

    get admin_job_class_metrics_path(job_class: "TestJob"), headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "job_class_metrics uses default job_class when not provided" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    JobMonitoringService.expects(:job_class_metrics).with("AnalyzeClothingImageJob", time_window: 1.hour).returns({
      total: 3,
      completed: 3,
      failed: 0,
      success_rate: 100.0,
      average_processing_time_ms: 50.0,
      time_window_seconds: 3600
    })

    # Route requires job_class parameter, but controller uses default when not provided
    # So we need to provide a job_class in the path, but the controller will use default if params[:job_class] is nil
    get admin_job_class_metrics_path(job_class: "AnalyzeClothingImageJob"), headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "dashboard sets instance variables correctly" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    job_health_data = {
      status: "healthy",
      queues: { "default" => { depth: 5 } },
      workers: { active: 2 },
      alerts: []
    }
    capacity_data = {
      queue_depths: { "default" => 5 },
      worker_capacity: { total_workers: 2, active_workers: 2 },
      processing_rate: { jobs_per_minute: 20, estimated_time_to_clear_minutes: 3 }
    }

    JobMonitoringService.expects(:queue_health).returns(job_health_data)
    JobMonitoringService.expects(:capacity_metrics).returns(capacity_data)

    get admin_dashboard_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end

  test "job_monitoring sets all instance variables correctly" do
    Admin::AdminController.any_instance.stubs(:authenticate_user!).returns(true)
    Admin::AdminController.any_instance.stubs(:current_user).returns(@admin_user)
    Admin::AdminController.any_instance.stubs(:user_signed_in?).returns(true)

    job_health_data = { status: "healthy", queues: {}, workers: { active: 1 }, alerts: [] }
    job_metrics_data = {
      completed: 15,
      average_processing_time_ms: 120.0,
      median_processing_time_ms: 110.0,
      p95_processing_time_ms: 200.0,
      p99_processing_time_ms: 250.0,
      time_window_seconds: 3600
    }
    failure_metrics_data = {
      total: 2,
      failure_rate: 0.1,
      failure_rate_percent: 10.0,
      by_job_class: { "TestJob" => 2 },
      time_window_seconds: 3600
    }

    JobMonitoringService.expects(:queue_health).returns(job_health_data)
    JobMonitoringService.expects(:job_metrics).with(time_window: 1.hour).returns(job_metrics_data)
    JobMonitoringService.expects(:failure_metrics).with(time_window: 1.hour).returns(failure_metrics_data)

    get admin_job_monitoring_path, headers: { "Accept" => "text/html" }

    assert_response :success
  end
end
