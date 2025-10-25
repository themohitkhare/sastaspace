# Additional factories for testing
FactoryBot.define do
  factory :export_job do
    user
    status { "pending" }
    file_format { "json" }
    requested_at { Time.current }

    trait :processing do
      status { "processing" }
      started_at { Time.current }
    end

    trait :completed do
      status { "completed" }
      started_at { 1.hour.ago }
      completed_at { Time.current }
    end

    trait :failed do
      status { "failed" }
      started_at { 1.hour.ago }
      failed_at { Time.current }
      error_message { "Export failed" }
    end
  end

  factory :audit_log do
    user
    action { "account_created" }
    ip_address { Faker::Internet.ip_v4_address }
    user_agent { Faker::Internet.user_agent }
    metadata { {} }

    trait :account_deleted do
      action { "account_deleted" }
    end

    trait :login do
      action { "login" }
    end

    trait :logout do
      action { "logout" }
    end
  end
end
