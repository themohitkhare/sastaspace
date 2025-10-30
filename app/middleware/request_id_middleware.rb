# Request ID middleware for correlation tracking
class RequestIdMiddleware
  def initialize(app)
    @app = app
  end

  def call(env)
    request_id = (env && env["HTTP_X_REQUEST_ID"]) || SecureRandom.uuid
    if env && env.respond_to?(:[]=)
      env["REQUEST_ID"] = request_id
    end

    # Set response header
    status, headers, response = @app.call(env)
    headers ||= {}
    if headers.respond_to?(:[]=)
      begin
        headers["X-Request-ID"] = request_id
      rescue StandardError
        # In case a non-standard headers object is returned, ignore setting the header
      end
    end

    [ status, headers, response ]
  end
end
