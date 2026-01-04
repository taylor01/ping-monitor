FactoryBot.define do
  factory :agent do
    sequence(:name) { |n| "agent-#{n}" }
    secret { "agent-secret-123" }
    description { "Test agent" }
    status { "active" }

    trait :suspended do
      status { "suspended" }
    end

    trait :deactivated do
      status { "deactivated" }
    end
  end
end
