# Suppress frozen string literal warnings from gems like marcel
# This warning comes from Ruby 3.4+ about future frozen string behavior
# The marcel gem uses string literals that will be frozen by default in future Ruby versions

# Suppress the deprecated warnings category (includes frozen string literal warnings)
Warning.suppress(:deprecated) if Warning.respond_to?(:suppress)

# Alternative: disable warnings entirely for the marcel gem operations
if defined?(Warning) && Warning.respond_to?(:[])
  Warning[:deprecated] = false
end

# More direct approach: silence the specific warning by overriding warn temporarily
original_warn = Warning.method(:warn)
Warning.singleton_class.send(:define_method, :warn) do |message, category: nil, **kwargs|
  # Skip the frozen string literal warning
  return if message.include?("literal string will be frozen in the future")
  original_warn.call(message, category: category, **kwargs)
end
