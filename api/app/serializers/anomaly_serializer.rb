class AnomalySerializer
  include JSONAPI::Serializer

  set_type :anomalies
  set_id :id

  attributes :host, :anomaly_type, :severity, :message, :current_value, :baseline_value, :resolved_at

  attribute :active do |anomaly|
    anomaly.active?
  end

  belongs_to :site
  belongs_to :measurement, if: proc { |record| record.measurement.present? }
end
