class Site < ApplicationRecord
  include TokenAuthenticatable

  # Associations
  has_many :measurements, dependent: :destroy
  has_many :baselines, dependent: :destroy
  has_many :anomalies, dependent: :destroy

  # Validations
  validates :name, presence: true, uniqueness: true
  validates :secret, presence: true, on: :create

  # Status enum
  enum :status, {
    unknown: "unknown",
    healthy: "healthy",
    warning: "warning",
    critical: "critical",
    offline: "offline"
  }, default: :unknown

  # Scopes
  scope :online, -> { where("last_heartbeat > ?", 5.minutes.ago) }
  scope :offline, -> { where("last_heartbeat <= ? OR last_heartbeat IS NULL", 5.minutes.ago) }

  # Methods
  def healthy?
    last_heartbeat.present? && last_heartbeat > 5.minutes.ago
  end

  def available_scopes
    %w[sites:read sites:write measurements:write anomalies:read]
  end

  def update_heartbeat!
    update!(last_heartbeat: Time.current, status: compute_status)
  end

  def active_anomalies
    anomalies.where(resolved_at: nil)
  end

  def active_critical_anomalies
    active_anomalies.where(severity: :critical)
  end

  def active_warning_anomalies
    active_anomalies.where(severity: :warning)
  end

  # Availability history methods
  def days_since_last_issue
    last_anomaly = anomalies.where.not(severity: :info).order(created_at: :desc).first
    return nil if last_anomaly.nil?

    ((Time.current - last_anomaly.created_at) / 1.day).floor
  end

  def availability_streak
    # Returns days since last warning/critical anomaly, or total monitoring days if none
    days_since_last_issue || days_monitored
  end

  def days_monitored
    first_measurement = measurements.order(:timestamp).first
    return 0 if first_measurement.nil?

    ((Time.current - first_measurement.timestamp) / 1.day).floor
  end

  private

  def compute_status
    return "offline" unless healthy?
    return "critical" if active_critical_anomalies.any?
    return "warning" if active_warning_anomalies.any?

    "healthy"
  end
end
