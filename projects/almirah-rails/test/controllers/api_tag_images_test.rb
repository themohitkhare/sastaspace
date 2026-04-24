require "test_helper"

# Controller test for POST /api/tag_images
#
# Uses a test double for AlmirahTagger so we never hit the real LiteLLM service
# in CI. Tests the auth gate (401 without session), the file validation path,
# and the happy-path JSON response.
class Api::TagImagesTest < ActionDispatch::IntegrationTest
  FIXTURE_TAG_RESULT = {
    "is_outfit_photo"  => true,
    "style_family"     => "ethnic-daily",
    "items_visible"    => [
      { "kind" => "kurta", "colour" => "indigo", "fabric_hint" => "cotton", "notes" => "block print" },
    ],
    "dominant_colours" => [ "indigo", "cream" ],
    "occasion_hint"    => "casual-day",
    "people_count"     => 1,
  }.freeze

  def setup
    @user = users(:test_user)
    # Build a minimal 1x1 JPEG fixture in memory (no file system needed).
    # Base64 of a 1x1 white JPEG.
    @fixture_jpeg = StringIO.new(
      Base64.decode64(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U" \
        "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN" \
        "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy" \
        "MjL/wAARCAABAAEDASIAAhEBAxEB/8QAFgABAQEAAAAAAAAAAAAAAAAABgUE/8QAHhAA" \
        "AgIDAQEBAQAAAAAAAAAAAQIDBAUREiH/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEB" \
        "AAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AmTEfD9OvVLqyFjkkWGCBHSsKzLPE" \
        "ZJ9T0TSRJSF5JpCTlk/FhJZGVhT0dFEuBRJHxXGYLCINY2IkYGPlJfH/9k="
      )
    )
    @fixture_jpeg.instance_variable_set(:@original_filename, "test.jpg")
    @fixture_jpeg.instance_variable_set(:@content_type, "image/jpeg")
    def @fixture_jpeg.content_type = "image/jpeg"
    def @fixture_jpeg.original_filename = "test.jpg"
    def @fixture_jpeg.size = length
  end

  # ------------------------------------------------------------------
  # Auth guard
  # ------------------------------------------------------------------

  test "returns 401 JSON when unauthenticated" do
    post api_tag_images_path, params: { image: fixture_file("test.jpg") }
    assert_response :unauthorized
    body = JSON.parse(response.body)
    assert_equal "unauthenticated", body["error"]
  end

  # ------------------------------------------------------------------
  # Validation guards (authenticated)
  # ------------------------------------------------------------------

  test "returns 400 when image param is missing" do
    sign_in_session
    post api_tag_images_path
    assert_response :bad_request
    body = JSON.parse(response.body)
    assert body["error"].present?
  end

  # ------------------------------------------------------------------
  # Happy path with mocked tagger
  # ------------------------------------------------------------------

  test "returns 200 with parsed tag JSON when tagger succeeds" do
    sign_in_session

    # Stub AlmirahTagger so no real HTTP call happens.
    mock_tagger = Minitest::Mock.new
    mock_tagger.expect(:tag, FIXTURE_TAG_RESULT, [String, { media_type: "image/jpeg" }])

    AlmirahTagger.stub(:new, mock_tagger) do
      jpeg_upload = fixture_file_upload(
        Rails.root.join("test", "fixtures", "files", "fixture.jpg"),
        "image/jpeg"
      )
      post api_tag_images_path, params: { image: jpeg_upload }
    end

    assert_response :success
    body = JSON.parse(response.body)
    assert body["ok"]
    assert_equal "ethnic-daily", body.dig("result", "style_family")
  end

  private

  def sign_in_session
    session_record = @user.sessions.create!(user_agent: "test", ip_address: "127.0.0.1")
    cookies.signed[:session_id] = session_record.id
  end

  def fixture_file(name)
    # Returns a minimal fixture upload for missing-param tests.
    Rack::Test::UploadedFile.new(
      StringIO.new(""),
      "image/jpeg",
      original_filename: name
    )
  end
end
