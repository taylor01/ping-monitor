FactoryBot.define do
  factory :baseline do
    site
    sequence(:host) { |n| "host-#{n}" }
    sequence(:ip) { |n| "192.168.1.#{n % 255}" }
    latency_mean { 25.0 }
    latency_stddev { 5.0 }
    latency_p95 { 35.0 }
    latency_p99 { 50.0 }
    sample_count { 100 }
    window_start { 24.hours.ago }
    window_end { Time.current }
  end
end
