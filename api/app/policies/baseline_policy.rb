class BaselinePolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    return true unless site?
    record.site_id == authenticatable.id
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      if site?
        # Sites only see their own baselines
        scope.where(site_id: authenticatable.id)
      else
        # Users, Agents, and ApiClients see all baselines
        scope.all
      end
    end
  end
end
