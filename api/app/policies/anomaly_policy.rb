class AnomalyPolicy < ApplicationPolicy
  def index?
    true
  end

  def show?
    # Sites can only see their own anomalies
    # Others can see all anomalies
    return true unless site?
    record.site_id == authenticatable.id
  end

  def resolve?
    # Sites can resolve their own anomalies
    # Operators/admins can resolve any anomaly
    # Agents can resolve anomalies (they have anomalies:write scope)
    return record.site_id == authenticatable.id if site?
    return true if agent?
    operator?
  end

  def history?
    true
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      if site?
        # Sites only see their own anomalies
        scope.where(site_id: authenticatable.id)
      else
        # Users, Agents, and ApiClients see all anomalies
        scope.all
      end
    end
  end
end
