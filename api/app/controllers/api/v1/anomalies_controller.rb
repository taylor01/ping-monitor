module Api
  module V1
    class AnomaliesController < BaseController
      # GET /api/v1/anomalies
      # List anomalies for current site
      def index
        anomalies = current_site.anomalies.order(created_at: :desc)

        anomalies = anomalies.active if params[:active] == "true"
        anomalies = anomalies.where(severity: params[:severity]) if params[:severity].present?
        anomalies = anomalies.limit(params[:limit] || 50)

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
    end
  end
end
