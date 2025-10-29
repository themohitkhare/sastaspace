# JWT token service for authentication
module Auth
  class JsonWebToken
    SECRET_KEY = Rails.application.credentials.secret_key_base || Rails.application.secret_key_base

    # Generate a short-lived access token (15 minutes)
    def self.encode_access_token(payload)
      encode(payload, exp: 15.minutes.from_now)
    end

    # Generate a longer-lived refresh token (30 days)
    def self.encode_refresh_token(payload)
      encode(payload, exp: 30.days.from_now)
    end

    def self.encode(payload, exp: 24.hours.from_now)
      payload[:exp] = exp.to_i
      JWT.encode(payload, SECRET_KEY)
    end

    def self.decode(token)
      decoded = JWT.decode(token, SECRET_KEY)[0]
      HashWithIndifferentAccess.new(decoded)
    rescue JWT::ExpiredSignature => e
      raise ExceptionHandler::ExpiredToken, "Token has expired"
    rescue JWT::DecodeError => e
      raise ExceptionHandler::InvalidToken, e.message
    end
  end
end
