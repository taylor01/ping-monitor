class IncidentPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    true
  end

  def create?
    # Only agents can create incidents
    agent?
  end

  def update?
    # Agents can update NC fields, users can update human fields
    agent? || user?
  end

  def resolve?
    # Agents can resolve incidents
    agent?
  end

  def review?
    # Users can add human review
    user?
  end

  def mark_reported?
    # Agents can mark as reported
    agent?
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      # Everyone can see all incidents (could scope by site if needed)
      scope.all
    end
  end
end
