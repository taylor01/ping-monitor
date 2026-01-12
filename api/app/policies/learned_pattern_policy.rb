class LearnedPatternPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    true
  end

  def create?
    # Agents and users can create patterns
    agent? || user?
  end

  def destroy?
    # Only users/admins can delete patterns
    user?
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      scope.all
    end
  end
end
