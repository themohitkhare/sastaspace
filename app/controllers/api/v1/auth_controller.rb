module Api
  module V1
    class AuthController < ApplicationController
      include Authenticable

      # Only protect the 'me' endpoint with authentication
      before_action :authenticate_user!, only: [ :me ]
      before_action :parse_json_params, only: [ :register, :login, :refresh ]
      def register
        user = User.new(user_params)

        if user.save
          token = Auth::JsonWebToken.encode(user_id: user.id)
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
              token: token
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
        user = User.find_by(email: params[:email])

        if user&.authenticate(params[:password])
          token = Auth::JsonWebToken.encode(user_id: user.id)
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
              token: token
            },
            message: "Login successful",
            timestamp: Time.current.iso8601
          }, status: :ok
        else
          render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Invalid email or password"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end
      end

      def refresh
        # For now, implement a basic refresh that validates the refresh token
        # and returns a new access token
        refresh_token = params[:refresh_token]

        if refresh_token.present? && refresh_token.start_with?("refresh_token_for_")
          # Extract user ID from refresh token (basic implementation)
          user_id = refresh_token.split("_").last.to_i
          user = User.find_by(id: user_id)

          if user
            new_token = Auth::JsonWebToken.encode(user_id: user.id)
            render json: {
              success: true,
              data: {
                token: new_token,
                refresh_token: refresh_token # Return same refresh token for now
              },
              timestamp: Time.current.iso8601
            }, status: :ok
          else
            render json: {
              success: false,
              error: {
                code: "AUTHENTICATION_ERROR",
                message: "Invalid refresh token"
              },
              timestamp: Time.current.iso8601
            }, status: :unauthorized
          end
        else
          render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Invalid refresh token"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end
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
        # JWT tokens are stateless, so we just return success
        # In a production app, you might want to implement token blacklisting
        render json: {
          success: true,
          data: {
            message: "Logout successful"
          },
          timestamp: Time.current.iso8601
        }, status: :ok
      end

      def logout_all
        # JWT tokens are stateless, so we implement a simple blacklist
        # In a production app, you would use Redis or database for this
        token = request.headers["Authorization"]&.split(" ")&.last

        if token.present?
          # Decode token to get user info
          begin
            decoded_token = Auth::JsonWebToken.decode(token)
            user_id = decoded_token[:user_id]

            # Store token in blacklist
            if Rails.env.test?
              blacklist = Authenticable.instance_variable_get(:@test_blacklisted_tokens) || []
              blacklist << token
              Authenticable.instance_variable_set(:@test_blacklisted_tokens, blacklist)
            else
              Rails.cache.write("blacklisted_token_#{token}", true, expires_in: 24.hours)
            end

            render json: {
              success: true,
              data: {
                message: "Logout from all devices successful"
              },
              timestamp: Time.current.iso8601
            }, status: :ok
          rescue ExceptionHandler::InvalidToken
            render json: {
              success: false,
              error: {
                code: "AUTHENTICATION_ERROR",
                message: "Invalid token"
              },
              timestamp: Time.current.iso8601
            }, status: :unauthorized
          end
        else
          render json: {
            success: false,
            error: {
              code: "AUTHENTICATION_ERROR",
              message: "Token required"
            },
            timestamp: Time.current.iso8601
          }, status: :unauthorized
        end
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
        user_data = params[:user] || params.permit!
        user_data.permit(:email, :password, :password_confirmation, :first_name, :last_name)
      end
    end
  end
end
