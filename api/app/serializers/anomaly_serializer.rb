class AnomalySerializer
  include JSONAPI::Serializer

  set_type :anomalies
  set_id :id

  attributes :host, :anomaly_type, :severity, :message, :current_value, :baseline_value, :resolved_at, :created_at

  attribute :active do |anomaly|
    anomaly.active?
  end

  attribute :duration do |anomaly|
    next nil unless anomaly.resolved_at
    seconds = (anomaly.resolved_at - anomaly.created_at).to_i
    if seconds < 60
      "#{seconds}s"
    elsif seconds < 3600
      "#{seconds / 60}m"
    else
      "#{seconds / 3600}h #{(seconds % 3600) / 60}m"
    end
  end

  belongs_to :site
  belongs_to :measurement, if: proc { |record| record.measurement.present? }
end
