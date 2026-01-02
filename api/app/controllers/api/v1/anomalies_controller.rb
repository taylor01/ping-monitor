module Api
  module V1
    class AnomaliesController < BaseController
      # GET /api/v1/anomalies
      # List anomalies for current site
      def index
        anomalies = current_site.anomalies.order(created_at: :desc)

        # Legacy filter (kept for backwards compatibility)
        anomalies = anomalies.active if params[:active] == "true"

        # Status filter for NC: active, resolved, or all
        case params[:status]
        when "active"
          anomalies = anomalies.active
        when "resolved"
          anomalies = anomalies.where.not(resolved_at: nil)
          # "all" or nil = no status filter
        end

        anomalies = anomalies.where(severity: params[:severity]) if params[:severity].present?

        # Since filter for efficient polling
        if params[:since].present?
          begin
            since_time = Time.parse(params[:since])
            anomalies = anomalies.where("updated_at > ?", since_time)
          rescue ArgumentError
            return render_jsonapi_error("Invalid since parameter format", status: :bad_request)
          end
        end

        anomalies = anomalies.limit(params[:limit] || 50)

        render json: AnomalySerializer.new(anomalies, meta: anomaly_meta).serializable_hash
      end

      # GET /api/v1/anomalies/history
      # Get historical anomalies for a device
      def history
        unless params[:host].present?
          return render_jsonapi_error("host parameter is required", status: :bad_request)
        end

        days = (params[:days] || 7).to_i
        since_date = days.days.ago

        anomalies = current_site.anomalies
                                .where(host: params[:host])
                                .where("created_at > ?", since_date)
                                .order(created_at: :desc)

        render json: AnomalySerializer.new(anomalies).serializable_hash
      end

      # GET /api/v1/anomalies/:id
      def show
        anomaly = current_site.anomalies.find(params[:id])
        render json: AnomalySerializer.new(anomaly).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Anomaly not found", status: :not_found)
      end

      # PATCH /api/v1/anomalies/:id/resolve
      def resolve
        anomaly = current_site.anomalies.find(params[:id])
        anomaly.resolve!
        render json: AnomalySerializer.new(anomaly).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Anomaly not found", status: :not_found)
      end

      private

      def anomaly_meta
        # Single aggregated query to avoid N+1
        counts = current_site.anomalies
                             .group("CASE WHEN resolved_at IS NULL THEN 'active' ELSE 'resolved' END")
                             .count
        {
          total: counts.values.sum,
          active: counts["active"] || 0,
          resolved: counts["resolved"] || 0
        }
      end
    end
  end
end
