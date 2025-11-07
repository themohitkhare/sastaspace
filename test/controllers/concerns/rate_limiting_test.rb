require "test_helper"

class RateLimitingTest < ActionDispatch::IntegrationTest
  # Test RateLimiting through a test controller
  class TestRateLimitController < Api::V1::BaseController
    include RateLimiting

    def index
      render json: { message: "success" }, status: :ok
    end
  end

  setup do
    @user = create(:user)
    @token = Auth::JsonWebToken.encode_access_token(user_id: @user.id)
    Rails.application.routes.draw do
      get "/test_rate_limit", to: "rate_limiting_test/test_rate_limit#index"
    end
  end

  teardown do
    Rails.application.routes_reloader.reload!
  end

  test "rate limiting is disabled in test environment" do
    # Rate limiting should be disabled in test, so requests should pass
    get "/test_rate_limit", headers: api_v1_headers(@token)
    assert_response :ok
  end

  test "rate_limit class method sets options" do
    controller_class = Class.new(ActionController::API) do
      include RateLimiting
      rate_limit limit: 50, period: 30, key_method: :current_user
    end

    options = controller_class.rate_limit_options
    assert_equal 50, options[:limit]
    assert_equal 30, options[:period]
    assert_equal :current_user, options[:key_method]
  end

  test "rate_limit_options returns defaults when not configured" do
    controller_class = Class.new(ActionController::API) do
      include RateLimiting
    end

    options = controller_class.rate_limit_options
    assert_equal 100, options[:limit]
    assert_equal 60, options[:period]
    assert_equal :current_user, options[:key_method]
  end

  test "rate_limit_key uses current_user when available" do
    controller = TestRateLimitController.new
    request_mock = mock("request")
    request_mock.stubs(:remote_ip).returns("127.0.0.1")
    controller.stubs(:current_user).returns(@user)
    controller.stubs(:request).returns(request_mock)

    key = controller.send(:rate_limit_key, :current_user)
    assert_equal "api:#{@user.id}", key
  end

  test "rate_limit_key uses IP when user not available" do
    controller = TestRateLimitController.new
    controller.stubs(:current_user).returns(nil)
    controller.stubs(:request).returns(mock(remote_ip: "192.168.1.1"))

    key = controller.send(:rate_limit_key, :current_user)
    assert_equal "api:192.168.1.1", key
  end

  test "get_rate_limit_count returns cached count" do
    # In test environment, cache is null_store, so we need to use memory store for this test
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    begin
      controller = TestRateLimitController.new
      cache_key = "rate_limit:test_key:60"
      Rails.cache.write(cache_key, 5, expires_in: 60.seconds)

      count = controller.send(:get_rate_limit_count, "test_key", 60)
      assert_equal 5, count
    ensure
      Rails.cache = original_cache
    end
  end

  test "get_rate_limit_count returns 0 when not cached" do
    controller = TestRateLimitController.new
    count = controller.send(:get_rate_limit_count, "nonexistent_key", 60)
    assert_equal 0, count
  end

  test "increment_rate_limit increments counter" do
    # In test environment, cache is null_store, so we need to use memory store for this test
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    begin
      controller = TestRateLimitController.new
      cache_key = "rate_limit:test_key:60"

      controller.send(:increment_rate_limit, "test_key", 60)
      count = Rails.cache.read(cache_key)
      assert_equal 1, count

      controller.send(:increment_rate_limit, "test_key", 60)
      count = Rails.cache.read(cache_key)
      assert_equal 2, count
    ensure
      Rails.cache = original_cache
    end
  end

  test "increment_rate_limit sets expiration" do
    # In test environment, cache is null_store, so we need to use memory store for this test
    original_cache = Rails.cache
    Rails.cache = ActiveSupport::Cache::MemoryStore.new

    begin
      controller = TestRateLimitController.new
      cache_key = "rate_limit:test_key:30"

      controller.send(:increment_rate_limit, "test_key", 30)
      assert Rails.cache.exist?(cache_key)
    ensure
      Rails.cache = original_cache
    end
  end

  private

  def api_v1_headers(token = nil)
    headers = { "Content-Type" => "application/json", "Accept" => "application/json" }
    headers.merge!("Authorization" => "Bearer #{token}") if token
    headers
  end
end
