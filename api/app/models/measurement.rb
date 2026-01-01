class Measurement < ApplicationRecord
  # Associations
  belongs_to :site
  has_many :anomalies, dependent: :nullify

  # Validations
  validates :host, presence: true
  validates :ip, presence: true
  validates :timestamp, presence: true
  validates :is_up, inclusion: { in: [ true, false ] }

  # Callbacks
  after_create :update_site_heartbeat

  # Scopes
  scope :up, -> { where(is_up: true) }
  scope :down, -> { where(is_up: false) }
  scope :recent, ->(since = 1.hour.ago) { where("timestamp > ?", since) }
  scope :for_host, ->(host) { where(host: host) }

  private

  def update_site_heartbeat
    site.update_heartbeat!
  end
end
