FactoryBot.define do
  factory :api_client do
    sequence(:name) { |n| "client-#{n}" }
    sequence(:client_id) { |n| "ac_test#{n}" }
    secret { "client-secret-123" }
    status { "active" }
    allowed_scopes { [ "sites:read" ] }

    trait :suspended do
      status { "suspended" }
    end

    trait :deactivated do
      status { "deactivated" }
    end

    trait :full_access do
      allowed_scopes { [ "*" ] }
    end
  end
end
