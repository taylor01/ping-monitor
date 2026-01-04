class ApiClient < ApplicationRecord
  include TokenAuthenticatable

  validates :name, presence: true
  validates :client_id, presence: true, uniqueness: true
  validates :secret, presence: true, on: :create

  enum :status, {
    active: "active",
    suspended: "suspended",
    deactivated: "deactivated"
  }, default: :active

  before_validation :generate_client_id, on: :create

  def can_authenticate?
    active?
  end

  def available_scopes
    allowed_scopes || []
  end

  private

  def generate_client_id
    self.client_id ||= "ac_#{SecureRandom.hex(16)}"
  end
end
