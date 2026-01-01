class Baseline < ApplicationRecord
  # Associations
  belongs_to :site

  # Validations
  validates :host, presence: true
  validates :host, uniqueness: { scope: :site_id }

  # Methods
  def latency_threshold_p95
    latency_p95 || 100.0  # Default 100ms if no baseline
  end

  def latency_threshold_p99
    latency_p99 || 200.0  # Default 200ms if no baseline
  end

  def exceeds_threshold?(latency_ms, percentile: :p95)
    return false if latency_ms.nil?

    threshold = percentile == :p99 ? latency_threshold_p99 : latency_threshold_p95
    latency_ms > threshold
  end
end
