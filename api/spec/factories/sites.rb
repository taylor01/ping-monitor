FactoryBot.define do
  factory :site do
    sequence(:name) { |n| "site-#{n}" }
    secret { "test-secret-123" }
    last_heartbeat { Time.current }
    status { "healthy" }
    topology_data { {} }

    trait :offline do
      last_heartbeat { 10.minutes.ago }
      status { "offline" }
    end

    trait :with_measurements do
      after(:create) do |site|
        create_list(:measurement, 5, site: site)
      end
    end
  end
end
