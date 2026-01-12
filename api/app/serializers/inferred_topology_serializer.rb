class InferredTopologySerializer
  include JSONAPI::Serializer

  attributes :upstream_device, :downstream_device,
             :confidence, :observed_count,
             :last_seen_at, :created_at, :updated_at

  belongs_to :site
end
