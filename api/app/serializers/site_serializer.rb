class SiteSerializer
  include JSONAPI::Serializer

  set_type :sites
  set_id :id

  attributes :name, :status, :last_heartbeat

  attribute :healthy do |site|
    site.healthy?
  end

  attribute :hosts_count do |site|
    site.measurements.select(:host).distinct.count
  end

  has_many :measurements, if: proc { |_record, params| params&.dig(:include_measurements) }
  has_many :anomalies, if: proc { |_record, params| params&.dig(:include_anomalies) }
end
