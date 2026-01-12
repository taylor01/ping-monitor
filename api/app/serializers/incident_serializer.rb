class IncidentSerializer
  include JSONAPI::Serializer

  attributes :started_at, :resolved_at, :auto_recovered,
             :nc_summary, :nc_root_cause_guess, :devices_affected,
             :human_root_cause, :human_notes, :human_reviewed_at,
             :severity, :reported_in_summary, :created_at, :updated_at

  attribute :active do |incident|
    incident.active?
  end

  attribute :pending_review do |incident|
    incident.pending_review?
  end

  attribute :duration_seconds do |incident|
    incident.duration&.to_i
  end

  belongs_to :site
end
