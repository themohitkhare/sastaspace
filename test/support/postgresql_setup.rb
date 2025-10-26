# test/support/postgresql_setup.rb

# PostgreSQL and pgvector test setup
class ActiveSupport::TestCase
  def setup
    # Ensure pgvector extension is available in test database
    begin
      ActiveRecord::Base.connection.execute('CREATE EXTENSION IF NOT EXISTS vector')
    rescue ActiveRecord::StatementInvalid => e
      if e.message.include?('extension "vector" does not exist')
        skip "pgvector extension not available in test database"
      else
        raise e
      end
    end
  end
end

# Helper methods for vector testing
module VectorTestHelpers
  def create_random_vector(dimensions = 1536)
    Array.new(dimensions) { rand(-1.0..1.0) }
  end

  def create_similar_vector(base_vector, similarity = 0.8)
    # Create a vector that's similar to the base vector
    base_vector.map { |val| val * similarity + rand(-0.2..0.2) }
  end

  def create_different_vector(base_vector)
    # Create a vector that's different from the base vector
    base_vector.map { |val| -val + rand(-0.5..0.5) }
  end

  def assert_vector_similarity(vector1, vector2, threshold = 0.7)
    # Calculate cosine similarity
    dot_product = vector1.zip(vector2).sum { |a, b| a * b }
    magnitude1 = Math.sqrt(vector1.sum { |v| v**2 })
    magnitude2 = Math.sqrt(vector2.sum { |v| v**2 })

    similarity = dot_product / (magnitude1 * magnitude2)
    assert similarity >= threshold, "Vector similarity #{similarity} is below threshold #{threshold}"
  end
end

# Include helpers in test classes
ActiveSupport::TestCase.include VectorTestHelpers
