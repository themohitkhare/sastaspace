module Api
  module V1
    class AuthController < BaseController
      # Only protect these endpoints with authentication
      before_action :authenticate_user!, only: [ :me, :logout, :logout_all ]
      before_action :parse_json_params, only: [ :register, :login, :refresh ]
      def register
        user = User.new(user_params)

        if user.save
          access_token = Auth::JsonWebToken.encode_access_token(user_id: user.id)
          refresh_token_record = RefreshToken.create_for_user!(user)

          render json: {
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
          }, status: :created
        else
          render json: {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "User creation failed",
              details: user.errors.as_json
            },
            timestamp: Time.current.iso8601
          }, status: :unprocessable_entity
        end
      end

      def login
        result = Auth::SessionService.login(
          params[:email],
          params[:password],
          request,
          remember_me: params[:remember_me] == true || params[:remember_me] == "true",
          ip_address: request.remote_ip
        )

        if result[:success]
          render json: result, status: :ok
        else
          status = result[:error][:code] == "ACCOUNT_LOCKED" ? :too_many_requests : :unauthorized
          render json: result, status: status
        end
      end

      def refresh
        refresh_token_param = params[:refresh_token]

        unless refresh_token_param.present?
          return render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Refresh token is required"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end

        # Find the refresh token in database
        refresh_token_record = RefreshToken.find_by(token: refresh_token_param)

        unless refresh_token_record
          return render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Invalid refresh token"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end

        # Check if token is blacklisted
        if refresh_token_record.blacklisted?
          return render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Refresh token has been revoked"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end

        # Check if token has expired
        unless refresh_token_record.active?
          return render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Refresh token has expired"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end

        # Get the user
        user = refresh_token_record.user

        # Blacklist the old refresh token (token rotation)
        refresh_token_record.blacklist!

        # Generate new tokens
        new_access_token = Auth::JsonWebToken.encode_access_token(user_id: user.id)
        new_refresh_token = RefreshToken.create_for_user!(user)

        render json: {
          success: true,
          data: {
            token: new_access_token,
            refresh_token: new_refresh_token.token
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      rescue ActiveRecord::RecordInvalid => e
        render json: {
          success: false,
          error: {
            code: "AUTHENTICATION_ERROR",
            message: "Failed to refresh token",
            details: e.message
          },
          timestamp: Time.current.iso8601
        }, status: :internal_server_error
      end

      def me
        # This endpoint should be protected by authentication
        # The Authenticable concern will handle the authentication
        render json: {
          success: true,
          data: {
            user: {
              id: current_user.id,
              email: current_user.email,
              first_name: current_user.first_name,
              last_name: current_user.last_name,
              created_at: current_user.created_at
            }
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      end

      def logout
        # Current user is available from authenticate_user! before_action
        token = request.headers["Authorization"]&.split(" ")&.last

        # Blacklist the current access token
        if Rails.env.test?
          blacklist = Authenticable.instance_variable_get(:@test_blacklisted_tokens) || []
          blacklist << token
          Authenticable.instance_variable_set(:@test_blacklisted_tokens, blacklist)
        else
          Rails.cache.write("blacklisted_token_#{token}", true, expires_in: 15.minutes)
        end

        render json: {
          success: true,
          data: {
            message: "Logout successful"
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      end

      def logout_all
        # Invalidate ALL refresh tokens for this user
        # This will force re-authentication on all devices
        current_user.invalidate_all_refresh_tokens!

        # Also blacklist the current access token
        token = request.headers["Authorization"]&.split(" ")&.last
        if Rails.env.test?
          blacklist = Authenticable.instance_variable_get(:@test_blacklisted_tokens) || []
          blacklist << token
          Authenticable.instance_variable_set(:@test_blacklisted_tokens, blacklist)
        else
          Rails.cache.write("blacklisted_token_#{token}", true, expires_in: 15.minutes)
        end

        render json: {
          success: true,
          data: {
            message: "Logout from all devices successful. All sessions have been invalidated."
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      end

      private

      def parse_json_params
        if request.content_type == "application/json"
          request.body.rewind
          json_params = JSON.parse(request.body.read)
          params.merge!(json_params)
        end
      rescue JSON::ParserError
        # If JSON parsing fails, continue with existing params
      end

      def user_params
        # Handle both nested (:user) and direct parameter formats
        # Also handle JSON requests
        if params[:user].present?
          params[:user].permit(:email, :password, :password_confirmation, :first_name, :last_name)
        else
          # For direct parameter format (from JSON), permit only the expected keys
          params.permit(:email, :password, :password_confirmation, :first_name, :last_name)
        end
      end
    end
  end
end
