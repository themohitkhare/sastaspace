# File signature validator
# Validates file types by checking actual file content, not just extension/content-type
# Prevents malicious files from being uploaded by checking magic bytes
class FileSignatureValidator
  # File signatures (magic bytes) for allowed image types
  SIGNATURES = {
    "image/jpeg" => [
      [ 0xFF, 0xD8, 0xFF ] # JPEG
    ],
    "image/png" => [
      [ 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A ] # PNG
    ],
    "image/webp" => [
      [ 0x52, 0x49, 0x46, 0x46 ] # WebP (RIFF header, need to check further)
    ]
  }.freeze

  # Validate file signature matches declared content type
  def self.valid?(file, declared_content_type)
    return false unless file.present? && declared_content_type.present?

    # Get file bytes
    file.rewind if file.respond_to?(:rewind)
    bytes = file.read(16) # Read first 16 bytes
    file.rewind if file.respond_to?(:rewind)

    return false if bytes.blank?

    # Check signatures for declared type
    signatures = SIGNATURES[declared_content_type]
    return false unless signatures

    # Check if file matches any signature for the declared type
    signatures.any? do |signature|
      bytes.byteslice(0, signature.length).bytes == signature
    end
  end

  # Detect actual file type from signature
  def self.detect_type(file)
    return nil unless file.present?

    file.rewind if file.respond_to?(:rewind)
    bytes = file.read(16)
    file.rewind if file.respond_to?(:rewind)

    return nil if bytes.blank?

    SIGNATURES.each do |content_type, signatures|
      signatures.each do |signature|
        if bytes.byteslice(0, signature.length).bytes == signature
          # For WebP, need additional check (RIFF...WEBP)
          if content_type == "image/webp"
            file.rewind if file.respond_to?(:rewind)
            webp_bytes = file.read(12)
            file.rewind if file.respond_to?(:rewind)
            return content_type if webp_bytes.include?("WEBP")
          else
            return content_type
          end
        end
      end
    end

    nil
  end
end
