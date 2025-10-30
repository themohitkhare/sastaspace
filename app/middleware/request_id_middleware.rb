# Request ID middleware for correlation tracking
class RequestIdMiddleware
  def initialize(app)
    @app = app
  end

  def call(env)
    request_id = env["HTTP_X_REQUEST_ID"] || SecureRandom.uuid
    env["REQUEST_ID"] = request_id

    # Set response header
    status, headers, response = @app.call(env)
    if headers && headers.respond_to?(:[]=)
      headers["X-Request-ID"] = request_id
    end

    [ status, headers, response ]
  end
end
