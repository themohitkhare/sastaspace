# frozen_string_literal: true

namespace :deploy do
  desc "Pre-deployment checks - validates system readiness before deployment"
  task pre_check: :environment do
    puts "🔍 Running pre-deployment checks..."
    puts ""

    errors = []
    warnings = []

    # 1. Database migrations safe?
    puts "📊 Checking database migrations..."
    begin
      pending = ActiveRecord::Base.connection.migration_context.needs_migration?
      if pending
        errors << "❌ Pending migrations detected! Run 'rails db:migrate' first."
      else
        puts "  ✅ No pending migrations"
      end
    rescue StandardError => e
      errors << "❌ Migration check failed: #{e.message}"
    end

    # 2. Database connection healthy?
    puts "💾 Checking database connection..."
    begin
      ActiveRecord::Base.connection.execute("SELECT 1")
      puts "  ✅ Database connection healthy"
    rescue StandardError => e
      errors << "❌ Database connection failed: #{e.message}"
    end

    # 3. Background jobs healthy?
    puts "⚙️  Checking background jobs (Redis/Sidekiq)..."
    begin
      if defined?(Sidekiq)
        Sidekiq.redis do |conn|
          conn.ping
        end
        puts "  ✅ Sidekiq/Redis operational"
      else
        require "redis"
        redis = Redis.new(url: ENV.fetch("REDIS_URL", "redis://127.0.0.1:6379/0"))
        redis.ping
        redis.close
        puts "  ✅ Redis operational"
      end
    rescue StandardError => e
      errors << "❌ Redis/Sidekiq not responding: #{e.message}"
    end

    # 4. Cache store operational?
    puts "🗄️  Checking cache store..."
    begin
      Rails.cache.write("deploy_check", "ok", expires_in: 1.minute)
      cached_value = Rails.cache.read("deploy_check")
      if cached_value == "ok"
        puts "  ✅ Cache store operational"
      else
        warnings << "⚠️  Cache read/write test failed (may still work)"
      end
    rescue StandardError => e
      warnings << "⚠️  Cache check failed: #{e.message}"
    end

    # 5. Ollama models available (only in production/staging)
    if Rails.env.production? || Rails.env.staging?
      puts "🤖 Checking Ollama models..."
      required_models = %w[mxbai-embed-large llava llama3.2]
      missing_models = []

      required_models.each do |model|
        begin
          # Check if ollama command is available
          result = system("which ollama > /dev/null 2>&1")
          unless result
            warnings << "⚠️  Ollama not found in PATH (AI features may not work)"
            break
          end

          # Check if model is available
          list_output = `ollama list 2>&1`
          if list_output.include?(model)
            puts "  ✅ Model '#{model}' available"
          else
            missing_models << model
          end
        rescue StandardError => e
          warnings << "⚠️  Could not check Ollama model '#{model}': #{e.message}"
        end
      end

      if missing_models.any?
        warnings << "⚠️  Missing Ollama models: #{missing_models.join(', ')} (AI features may not work)"
      end
    else
      puts "🤖 Skipping Ollama check (not in production/staging)"
    end

    # 6. Environment variables check
    puts "🔐 Checking critical environment variables..."
    critical_env_vars = %w[SECRET_KEY_BASE DATABASE_URL]
    missing_env_vars = []

    critical_env_vars.each do |var|
      if ENV[var].blank?
        missing_env_vars << var
      else
        puts "  ✅ #{var} is set"
      end
    end

    if missing_env_vars.any?
      errors << "❌ Missing critical environment variables: #{missing_env_vars.join(', ')}"
    end

    # 7. Check for pending Sidekiq jobs (warning only)
    if defined?(Sidekiq)
      puts "📋 Checking Sidekiq queue status..."
      begin
        Sidekiq.redis do |conn|
          queue_sizes = {}
          %w[default ai_critical low_priority].each do |queue|
            size = conn.llen("queue:#{queue}")
            queue_sizes[queue] = size if size > 0
          end

          if queue_sizes.any?
            total = queue_sizes.values.sum
            if total > 1000
              warnings << "⚠️  Large number of pending jobs (#{total} total) - may indicate issues"
            else
              puts "  ✅ Queue sizes normal (#{total} pending jobs)"
            end
          else
            puts "  ✅ No pending jobs"
          end
        end
      rescue StandardError => e
        warnings << "⚠️  Could not check Sidekiq queues: #{e.message}"
      end
    end

    # 8. Database constraints check (verify foreign keys, etc.)
    puts "🔗 Checking database constraints..."
    begin
      # Check if we can query a sample of key tables
      %w[users inventory_items outfits].each do |table|
        ActiveRecord::Base.connection.execute("SELECT COUNT(*) FROM #{table} LIMIT 1")
      end
      puts "  ✅ Database schema accessible"
    rescue StandardError => e
      errors << "❌ Database schema check failed: #{e.message}"
    end

    # Summary
    puts ""
    puts "=" * 60
    puts "📋 Pre-Deployment Check Summary"
    puts "=" * 60

    if errors.empty? && warnings.empty?
      puts "✅ All checks passed! Ready for deployment."
      puts ""
      exit 0
    else
      if errors.any?
        puts ""
        puts "❌ ERRORS (must be fixed before deployment):"
        errors.each { |error| puts "  #{error}" }
      end

      if warnings.any?
        puts ""
        puts "⚠️  WARNINGS (review before deployment):"
        warnings.each { |warning| puts "  #{warning}" }
      end

      puts ""
      if errors.any?
        puts "🚫 Deployment blocked due to errors above."
        exit 1
      else
        puts "⚠️  Deployment can proceed, but review warnings above."
        exit 0
      end
    end
  end

  desc "Post-deployment verification - checks system health after deployment"
  task post_check: :environment do
    puts "🔍 Running post-deployment verification..."
    puts ""

    # Use existing health checker
    health_status = HealthChecker.check_all

    if health_status[:status] == "healthy"
      puts "✅ All services healthy after deployment"
      health_status[:services].each do |service, status|
        if status[:status] == "healthy"
          puts "  ✅ #{service.to_s.humanize}: #{status[:message]}"
        else
          puts "  ❌ #{service.to_s.humanize}: #{status[:error]}"
        end
      end
      puts ""
      puts "✅ Deployment verification successful!"
      exit 0
    else
      puts "❌ Deployment verification failed!"
      health_status[:services].each do |service, status|
        if status[:status] != "healthy"
          puts "  ❌ #{service.to_s.humanize}: #{status[:error]}"
        end
      end
      puts ""
      puts "🚫 System is not healthy after deployment. Review logs."
      exit 1
    end
  end

  desc "Full deployment check (pre + post)"
  task check: [:pre_check, :post_check] do
    puts ""
    puts "✅ Full deployment check completed!"
  end
end
