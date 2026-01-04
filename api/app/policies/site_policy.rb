class SitePolicy < ApplicationPolicy
  def index?
    # All authenticated entities can list sites
    true
  end

  def show?
    # All authenticated entities can view any site
    true
  end

  def me?
    # Only sites can view "me" endpoint (their own data)
    site?
  end

  def status?
    # All authenticated entities can view site status
    true
  end

  class Scope < ApplicationPolicy::Scope
    def resolve
      if site?
        # Sites only see themselves
        scope.where(id: authenticatable.id)
      else
        # Users, Agents, and ApiClients see all sites
        scope.all
      end
    end
  end
end
