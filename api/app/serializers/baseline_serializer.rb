class BaselineSerializer
  include JSONAPI::Serializer

  set_type :baselines
  set_id :host

  attributes :host, :ip, :latency_mean, :latency_stddev, :latency_p95, :latency_p99,
             :sample_count, :window_start, :window_end

  attribute :thresholds do |baseline|
    {
      warning: baseline.latency_p95 ? (baseline.latency_p95 * 1.5).round(2) : nil,
      critical: baseline.latency_p95 ? (baseline.latency_p95 * 2.0).round(2) : nil
    }
  end

  belongs_to :site
end
