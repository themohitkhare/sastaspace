require "test_helper"

class HealthControllerTest < ActionDispatch::IntegrationTest
  test "GET /health returns healthy status when all services are healthy" do
    HealthChecker.stubs(:check_all).returns({
      status: "healthy",
      timestamp: Time.current.iso8601,
      services: {
        database: { status: "healthy" },
        cache: { status: "healthy" },
        jobs: { status: "healthy" }
      }
    })

    get "/health"

    assert_response :ok
    body = JSON.parse(@response.body)
    assert_equal "healthy", body["status"]
    assert body["timestamp"].present?
    assert body["services"].present?
  end

  test "GET /health returns service_unavailable when services are unhealthy" do
    HealthChecker.stubs(:check_all).returns({
      status: "unhealthy",
      timestamp: Time.current.iso8601,
      services: {
        database: { status: "healthy" },
        cache: { status: "unhealthy", error: "Cache connection failed" },
        jobs: { status: "healthy" }
      }
    })

    get "/health"

    assert_response :service_unavailable
    body = JSON.parse(@response.body)
    assert_equal "unhealthy", body["status"]
  end

  test "GET /health includes all service statuses" do
    HealthChecker.stubs(:check_all).returns({
      status: "healthy",
      timestamp: Time.current.iso8601,
      services: {
        database: { status: "healthy", message: "Database connection successful" },
        cache: { status: "healthy", message: "Cache store operational" },
        jobs: { status: "healthy", message: "Job queue operational" }
      }
    })

    get "/health"

    assert_response :ok
    body = JSON.parse(@response.body)
    assert body["services"]["database"].present?
    assert body["services"]["cache"].present?
    assert body["services"]["jobs"].present?
  end
end
