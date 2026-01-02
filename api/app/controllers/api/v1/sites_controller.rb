require "ostruct"

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

      # GET /api/v1/sites/:id/status
      # Get site status summary for NC
      def status
        site = Site.find(params[:id])
        status_data = build_site_status(site)
        render json: SiteStatusSerializer.new(status_data).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      end

      private

      def build_site_status(site)
        # Get latest measurement per host (works with both PostgreSQL and SQLite)
        latest_measurements = latest_measurements_for_site(site)

        devices_up = latest_measurements.count(&:is_up)
        devices_down = latest_measurements.count { |m| !m.is_up }
        active_anomalies = site.anomalies.active.count

        overall_status = if devices_down.zero?
                           "healthy"
        elsif devices_down > devices_up
                           "critical"
        else
                           "degraded"
        end

        OpenStruct.new(
          id: site.id,
          name: site.name,
          status: overall_status,
          devices_total: latest_measurements.size,
          devices_up: devices_up,
          devices_down: devices_down,
          active_anomalies: active_anomalies,
          last_data_at: site.last_heartbeat,
          devices: latest_measurements.map do |m|
            {
              host: m.host,
              ip: m.ip,
              is_up: m.is_up,
              latency_ms: m.latency_ms,
              packet_loss: m.packet_loss
            }
          end
        )
      end

      def latest_measurements_for_site(site)
        # Get the latest measurement for each host
        # Using a subquery approach that works with both PostgreSQL and SQLite
        subquery = site.measurements
                       .select("host, MAX(timestamp) as max_timestamp")
                       .group(:host)

        site.measurements
            .joins("INNER JOIN (#{subquery.to_sql}) latest ON measurements.host = latest.host AND measurements.timestamp = latest.max_timestamp")
            .distinct
      end
    end
  end
end
