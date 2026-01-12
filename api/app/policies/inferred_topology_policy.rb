class InferredTopologyPolicy < ApplicationPolicy
  def index?
    true
  end

  def for_device?
    true
  end

  def create?
    # Only agents can record topology inferences
    agent?
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      scope.all
    end
  end
end
