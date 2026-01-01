FactoryBot.define do
  factory :measurement do
    site
    sequence(:host) { |n| "host-#{n}" }
    sequence(:ip) { |n| "192.168.1.#{n % 255}" }
    timestamp { Time.current }
    latency_ms { rand(1.0..50.0).round(2) }
    packet_loss { 0.0 }
    jitter_ms { rand(0.1..5.0).round(2) }
    is_up { true }

    trait :down do
      is_up { false }
      latency_ms { nil }
      packet_loss { 100.0 }
      jitter_ms { nil }
    end

    trait :high_latency do
      latency_ms { rand(200.0..500.0).round(2) }
    end
  end
end
