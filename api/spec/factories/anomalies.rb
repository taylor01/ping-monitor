FactoryBot.define do
  factory :anomaly do
    site
    measurement { nil }
    sequence(:host) { |n| "host-#{n}" }
    anomaly_type { :host_down }
    severity { :warning }
    current_value { nil }
    baseline_value { nil }
    message { "Host is unreachable" }
    context_snapshot { {} }
    resolved_at { nil }

    trait :critical do
      severity { :critical }
    end

    trait :resolved do
      resolved_at { Time.current }
    end

    trait :latency_spike do
      anomaly_type { :latency_spike }
      current_value { 250.0 }
      baseline_value { 25.0 }
      message { "Latency spike detected: 250ms (baseline: 25ms)" }
    end

    trait :site_offline do
      anomaly_type { :site_offline }
      severity { :critical }
      host { nil }
      message { "Site has stopped reporting" }
    end
  end
end
