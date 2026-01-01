class Anomaly < ApplicationRecord
  # Associations
  belongs_to :site
  belongs_to :measurement, optional: true
  has_many :analysis_logs, dependent: :destroy

  # Enums
  enum :anomaly_type, {
    host_down: 0,
    host_recovery: 1,
    latency_spike: 2,
    packet_loss: 3,
    site_offline: 4
  }

  enum :severity, {
    info: 0,
    warning: 1,
    critical: 2
  }

  # Validations
  validates :anomaly_type, presence: true
  validates :severity, presence: true

  # Scopes
  scope :active, -> { where(resolved_at: nil) }
  scope :resolved, -> { where.not(resolved_at: nil) }
  scope :critical, -> { where(severity: :critical) }
  scope :recent, ->(since = 24.hours.ago) { where("created_at > ?", since) }

  # Methods
  def active?
    resolved_at.nil?
  end

  def resolve!
    update!(resolved_at: Time.current)
  end
end
