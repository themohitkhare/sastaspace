require "test_helper"

class InputSanitizerTest < ActiveSupport::TestCase
  test "sanitize_html removes dangerous tags" do
    html = "<script>alert('xss')</script><p>Safe content</p>"
    sanitized = InputSanitizer.sanitize_html(html)
    assert_not_includes sanitized, "<script>"
    assert_includes sanitized, "<p>Safe content</p>"
  end

  test "sanitize_html allows safe tags" do
    html = "<p>Paragraph</p><strong>Bold</strong><em>Italic</em>"
    sanitized = InputSanitizer.sanitize_html(html)
    assert_includes sanitized, "<p>"
    assert_includes sanitized, "<strong>"
    assert_includes sanitized, "<em>"
  end

  test "sanitize_text removes all HTML" do
    html = "<p>Text</p><script>alert('xss')</script>"
    sanitized = InputSanitizer.sanitize_text(html)
    assert_not_includes sanitized, "<"
    assert_not_includes sanitized, ">"
    assert_includes sanitized, "Text"
  end

  test "sanitize_filename removes path traversal" do
    filename = "../../etc/passwd"
    sanitized = InputSanitizer.sanitize_filename(filename)
    assert_equal "passwd", sanitized
  end

  test "sanitize_filename removes special characters" do
    filename = "file<>name|with*special:chars?.txt"
    sanitized = InputSanitizer.sanitize_filename(filename)
    assert_not_includes sanitized, "<"
    assert_not_includes sanitized, ">"
    assert_not_includes sanitized, "|"
  end

  test "sanitize_email normalizes email" do
    email = "  Test@Example.COM  "
    sanitized = InputSanitizer.sanitize_email(email)
    assert_equal "test@example.com", sanitized
  end

  test "sanitize_url only allows http/https" do
    assert_equal "https://example.com", InputSanitizer.sanitize_url("https://example.com")
    assert_equal "http://example.com", InputSanitizer.sanitize_url("http://example.com")
    assert_nil InputSanitizer.sanitize_url("javascript:alert('xss')")
    assert_nil InputSanitizer.sanitize_url("file:///etc/passwd")
  end
end
