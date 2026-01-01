class Site < ApplicationRecord
  # Associations
  has_many :measurements, dependent: :destroy
  has_many :baselines, dependent: :destroy
  has_many :anomalies, dependent: :destroy

  # Authentication - uses bcrypt for secret hashing
  has_secure_password :secret, validations: false

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

  private

  def compute_status
    return "offline" unless healthy?
    return "critical" if active_critical_anomalies.any?
    return "warning" if active_warning_anomalies.any?

    "healthy"
  end
end
