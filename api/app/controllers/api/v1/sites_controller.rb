module Api
  module V1
    class SitesController < BaseController
      # GET /api/v1/sites
      # List all sites (admin view - typically would need admin auth)
      def index
        sites = Site.all.order(:name)
        render json: SiteSerializer.new(sites).serializable_hash
      end

      # GET /api/v1/sites/:id
      def show
        site = Site.find(params[:id])
        options = {
          include_measurements: params[:include]&.include?("measurements"),
          include_anomalies: params[:include]&.include?("anomalies")
        }
        render json: SiteSerializer.new(site, params: options).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      end

      # GET /api/v1/sites/me
      # Get current site info (authenticated site)
      def me
        render json: SiteSerializer.new(current_site).serializable_hash
      end
    end
  end
end
