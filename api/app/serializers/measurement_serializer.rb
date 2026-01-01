class MeasurementSerializer
  include JSONAPI::Serializer

  set_type :measurements
  set_id :id

  attributes :host, :ip, :timestamp, :latency_ms, :packet_loss, :jitter_ms, :is_up

  belongs_to :site
end
