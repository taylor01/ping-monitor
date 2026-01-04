module Api
  module V1
    class BaselinesController < BaseController
      def index
        baselines = policy_scope(Baseline).order(:host)
        render json: BaselineSerializer.new(baselines).serializable_hash
      end

      def show
        baseline = policy_scope(Baseline).find_by!(host: params[:host])
        render json: BaselineSerializer.new(baseline).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error(
          "No baseline exists for the specified host",
          status: :not_found,
          code: "not_found"
        )
      end
    end
  end
end
