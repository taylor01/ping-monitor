class LearnedPatternSerializer
  include JSONAPI::Serializer

  attributes :device, :pattern_type, :description,
             :confidence, :occurrences, :time_pattern,
             :last_seen_at, :created_at, :updated_at

  attribute :site_wide do |pattern|
    pattern.device.nil?
  end

  belongs_to :site
end
