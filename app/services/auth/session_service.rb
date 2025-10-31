# Service to handle authentication by directly using the auth logic
# Instead of making HTTP calls or instantiating controllers, we reuse the logic
module Auth
  class SessionService
    def self.login(email, password, _original_request = nil, remember_me: false)
      user = User.find_by(email: email)

      if user&.authenticate(password)
        access_token = Auth::JsonWebToken.encode_access_token(user_id: user.id)
        # Set refresh token expiration based on remember_me
        refresh_token_expires_in = remember_me ? 30.days : 7.days
        refresh_token_record = RefreshToken.create_for_user!(user, expires_in: refresh_token_expires_in)

        {
          success: true,
          data: {
            user: {
              id: user.id,
              email: user.email,
              first_name: user.first_name,
              last_name: user.last_name,
              created_at: user.created_at
            },
            token: access_token,
            refresh_token: refresh_token_record.token
          },
          message: "Login successful",
          timestamp: Time.current.iso8601
        }
      else
        {
          success: false,
          error: {
            code: "AUTHENTICATION_ERROR",
            message: "Invalid email or password"
          },
          timestamp: Time.current.iso8601
        }
      end
    rescue StandardError => e
      Rails.logger.error "Login service error: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")
      {
        success: false,
        error: {
          code: "AUTHENTICATION_ERROR",
          message: "Login failed: #{e.message}",
          details: {}
        }
      }
    end

    def self.register(user_params_hash, _original_request = nil)
      user = User.new(
        email: user_params_hash[:email] || user_params_hash["email"],
        first_name: user_params_hash[:first_name] || user_params_hash["first_name"],
        last_name: user_params_hash[:last_name] || user_params_hash["last_name"],
        password: user_params_hash[:password] || user_params_hash["password"],
        password_confirmation: user_params_hash[:password_confirmation] || user_params_hash["password_confirmation"]
      )

      if user.save
        access_token = Auth::JsonWebToken.encode_access_token(user_id: user.id)
        refresh_token_record = RefreshToken.create_for_user!(user)

        {
          success: true,
          data: {
            user: {
              id: user.id,
              email: user.email,
              first_name: user.first_name,
              last_name: user.last_name,
              created_at: user.created_at
            },
            token: access_token,
            refresh_token: refresh_token_record.token
          },
          message: "User created successfully",
          timestamp: Time.current.iso8601
        }
      else
        {
          success: false,
          error: {
            code: "VALIDATION_ERROR",
            message: "User creation failed",
            details: user.errors.as_json
          },
          timestamp: Time.current.iso8601
        }
      end
    rescue StandardError => e
      Rails.logger.error "Registration service error: #{e.message}"
      Rails.logger.error e.backtrace.join("\n")
      {
        success: false,
        error: {
          code: "REGISTRATION_ERROR",
          message: "Registration failed: #{e.message}",
          details: {}
        }
      }
    end
  end
end
