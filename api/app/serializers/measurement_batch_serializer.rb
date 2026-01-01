class MeasurementBatchSerializer
  include JSONAPI::Serializer

  set_type :"measurement-batches"
  set_id { |batch| batch[:id] }

  attribute :count do |batch|
    batch[:count]
  end

  attribute :site_name do |batch|
    batch[:site_name]
  end

  attribute :timestamp do |batch|
    batch[:timestamp]
  end
end
