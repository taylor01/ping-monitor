class InferredTopology < ApplicationRecord
  belongs_to :site

  # Validations
  validates :upstream_device, presence: true
  validates :downstream_device, presence: true
  validates :confidence, numericality: { greater_than_or_equal_to: 0, less_than_or_equal_to: 1 }
  validates :upstream_device, uniqueness: { scope: [ :site_id, :downstream_device ] }

  # Scopes
  scope :confident, -> { where("confidence >= 0.5") }
  scope :for_upstream, ->(device) { where(upstream_device: device) }

  # Record or update a topology inference
  def self.record!(site:, upstream_device:, downstream_devices:)
    # Batch load all existing records to avoid N+1 queries
    existing = where(
      site: site,
      upstream_device: upstream_device,
      downstream_device: downstream_devices
    ).index_by(&:downstream_device)

    downstream_devices.each do |downstream|
      topology = existing[downstream] || new(
        site: site,
        upstream_device: upstream_device,
        downstream_device: downstream
      )

      if topology.persisted?
        topology.observed_count += 1
        topology.confidence = [ 0.95, topology.confidence + 0.15 ].min
      end

      topology.last_seen_at = Time.current
      topology.save!
    end
  end

  # Get downstream devices for an upstream device
  def self.downstream_for(site:, upstream_device:)
    where(site: site, upstream_device: upstream_device)
      .confident
      .pluck(:downstream_device)
  end

  # Get topology as hash: { upstream => [downstream1, downstream2, ...] }
  def self.as_hash(site:)
    confident.where(site: site)
             .group_by(&:upstream_device)
             .transform_values { |records| records.map(&:downstream_device) }
  end
end
