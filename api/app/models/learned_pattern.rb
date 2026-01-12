class LearnedPattern < ApplicationRecord
  belongs_to :site

  # Pattern types that NC can learn
  PATTERN_TYPES = %w[
    scheduled_downtime
    cascade_source
    flaky
    normal_reboot
    weather_sensitive
  ].freeze

  # Validations
  validates :pattern_type, presence: true, inclusion: { in: PATTERN_TYPES }
  validates :description, presence: true
  validates :confidence, numericality: { greater_than_or_equal_to: 0, less_than_or_equal_to: 1 }

  # Scopes
  scope :for_device, ->(device) { where(device: device) }
  scope :site_wide, -> { where(device: nil) }
  scope :confident, -> { where("confidence >= 0.7") }

  # Record or update a pattern
  def self.record!(site:, pattern_type:, description:, device: nil, time_pattern: nil)
    pattern = find_or_initialize_by(site: site, device: device, pattern_type: pattern_type)

    if pattern.persisted?
      pattern.occurrences += 1
      pattern.confidence = [ 0.95, pattern.confidence + 0.1 ].min
    end

    pattern.description = description
    pattern.time_pattern = time_pattern if time_pattern
    pattern.last_seen_at = Time.current
    pattern.save!
    pattern
  end
end
