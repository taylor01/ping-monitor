class ApplicationPolicy
  attr_reader :authenticatable, :record

  def initialize(authenticatable, record)
    @authenticatable = authenticatable
    @record = record
  end

  def index?
    false
  end

  def show?
    false
  end

  def create?
    false
  end

  def update?
    false
  end

  def destroy?
    false
  end

  class Scope
    attr_reader :authenticatable, :scope

    def initialize(authenticatable, scope)
      @authenticatable = authenticatable
      @scope = scope
    end

    def resolve
      raise NotImplementedError, "You must define #resolve in #{self.class}"
    end

    private

    def site?
      authenticatable.is_a?(Site)
    end

    def user?
      authenticatable.is_a?(User)
    end

    def agent?
      authenticatable.is_a?(Agent)
    end

    def api_client?
      authenticatable.is_a?(ApiClient)
    end

    def admin?
      user? && authenticatable.admin?
    end
  end

  private

  def site?
    authenticatable.is_a?(Site)
  end

  def user?
    authenticatable.is_a?(User)
  end

  def agent?
    authenticatable.is_a?(Agent)
  end

  def api_client?
    authenticatable.is_a?(ApiClient)
  end

  def admin?
    user? && authenticatable.admin?
  end

  def operator?
    user? && (authenticatable.admin? || authenticatable.operator?)
  end
end
