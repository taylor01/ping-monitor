class Agent < ApplicationRecord
  include TokenAuthenticatable

  validates :name, presence: true, uniqueness: true
  validates :secret, presence: true, on: :create

  enum :status, {
    active: "active",
    suspended: "suspended",
    deactivated: "deactivated"
  }, default: :active

  def can_authenticate?
    active?
  end

  def available_scopes
    %w[sites:read anomalies:read anomalies:write]
  end
end
