module TokenAuthenticatable
  extend ActiveSupport::Concern

  included do
    has_secure_password :secret, validations: false
  end

  # Each model must implement this to define its available scopes
  def available_scopes
    raise NotImplementedError, "#{self.class.name} must implement #available_scopes"
  end

  def can_authenticate?
    true
  end

  # Validate requested scopes against what this authenticatable is allowed
  def validate_scopes(requested_scopes)
    return available_scopes if requested_scopes.blank?
    allowed = available_scopes
    return allowed if allowed.include?("*")
    requested_scopes.select { |s| allowed.include?(s) }
  end
end
