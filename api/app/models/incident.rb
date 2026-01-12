class Incident < ApplicationRecord
  belongs_to :site

  # Enums
  enum :severity, {
    normal: "normal",
    major: "major"
  }, default: :normal

  # Validations
  validates :started_at, presence: true
  validates :severity, presence: true

  # Scopes
  scope :active, -> { where(resolved_at: nil) }
  scope :resolved, -> { where.not(resolved_at: nil) }
  scope :pending_review, -> { resolved.where(human_reviewed_at: nil) }
  scope :not_reported, -> { where(reported_in_summary: false) }
  scope :since, ->(time) { where("started_at > ?", time) }

  # Methods
  def active?
    resolved_at.nil?
  end

  def resolved?
    resolved_at.present?
  end

  def pending_review?
    resolved? && human_reviewed_at.nil?
  end

  def resolve!(auto_recovered: false, nc_summary: nil)
    update!(
      resolved_at: Time.current,
      auto_recovered: auto_recovered,
      nc_summary: nc_summary || self.nc_summary
    )
  end

  def add_human_review!(root_cause:, notes: nil)
    update!(
      human_root_cause: root_cause,
      human_notes: notes,
      human_reviewed_at: Time.current
    )
  end

  def mark_reported!
    update!(reported_in_summary: true)
  end

  def duration
    return nil unless resolved_at && started_at
    resolved_at - started_at
  end
end
