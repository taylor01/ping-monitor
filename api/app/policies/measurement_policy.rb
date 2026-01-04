class MeasurementPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    return true unless site?
    record.site_id == authenticatable.id
  end

  def create?
    # Only Sites can create measurements for themselves
    site?
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      if site?
        # Sites only see their own measurements
        scope.where(site_id: authenticatable.id)
      else
        # Users, Agents, and ApiClients see all measurements
        scope.all
      end
    end
  end
end
