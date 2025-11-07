require "test_helper"

class FileSignatureValidatorTest < ActiveSupport::TestCase
  test "valid? returns true for valid JPEG file" do
    # Create a minimal JPEG file (just the signature)
    jpeg_file = StringIO.new([ 0xFF, 0xD8, 0xFF, 0xE0 ].pack("C*"))
    assert FileSignatureValidator.valid?(jpeg_file, "image/jpeg")
  end

  test "valid? returns true for valid PNG file" do
    # Create a minimal PNG file (just the signature)
    png_signature = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]
    png_file = StringIO.new(png_signature.pack("C*"))
    assert FileSignatureValidator.valid?(png_file, "image/png")
  end

  test "valid? returns false for mismatched type" do
    # PNG signature but declared as JPEG
    png_signature = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]
    png_file = StringIO.new(png_signature.pack("C*"))
    assert_not FileSignatureValidator.valid?(png_file, "image/jpeg")
  end

  test "valid? returns false for invalid file" do
    invalid_file = StringIO.new("not an image")
    assert_not FileSignatureValidator.valid?(invalid_file, "image/jpeg")
  end

  test "detect_type detects JPEG" do
    jpeg_file = StringIO.new([ 0xFF, 0xD8, 0xFF, 0xE0 ].pack("C*"))
    assert_equal "image/jpeg", FileSignatureValidator.detect_type(jpeg_file)
  end

  test "detect_type detects PNG" do
    png_signature = [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ]
    png_file = StringIO.new(png_signature.pack("C*"))
    assert_equal "image/png", FileSignatureValidator.detect_type(png_file)
  end

  test "detect_type returns nil for unknown type" do
    unknown_file = StringIO.new("unknown content")
    assert_nil FileSignatureValidator.detect_type(unknown_file)
  end
end
