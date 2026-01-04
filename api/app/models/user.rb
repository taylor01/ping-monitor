class User < ApplicationRecord
  has_secure_password

  validates :email, presence: true, uniqueness: true,
            format: { with: URI::MailTo::EMAIL_REGEXP }

  enum :role, {
    viewer: "viewer",
    operator: "operator",
    admin: "admin"
  }, default: :viewer

  def can_authenticate?
    true
  end

  def available_scopes
    case role
    when "admin" then %w[*]
    when "operator" then %w[sites:read anomalies:read anomalies:write]
    else %w[sites:read anomalies:read]
    end
  end

  def validate_scopes(requested_scopes)
    return available_scopes if requested_scopes.blank?
    allowed = available_scopes
    return allowed if allowed.include?("*")
    requested_scopes.select { |s| allowed.include?(s) }
  end
end
