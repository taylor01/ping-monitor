FactoryBot.define do
  factory :user do
    sequence(:email) { |n| "user#{n}@example.com" }
    password { "password123" }
    name { "Test User" }
    role { "viewer" }

    trait :admin do
      role { "admin" }
    end

    trait :operator do
      role { "operator" }
    end
  end
end
