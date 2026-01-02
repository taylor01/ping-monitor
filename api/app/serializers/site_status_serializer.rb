class SiteStatusSerializer
  include JSONAPI::Serializer

  set_type :site_status
  set_id :id

  attributes :name, :status, :devices_total, :devices_up, :devices_down,
             :active_anomalies, :last_data_at, :devices
end
