module Api
  module V1
    class MeasurementsController < BaseController
      # POST /api/v1/measurements
      # Receive measurement batch from a ping monitor
      def create
        batch_data = measurement_params

        measurements = build_measurements(batch_data)

        if measurements.all?(&:valid?)
          Measurement.transaction do
            measurements.each(&:save!)
          end

          batch_result = {
            id: SecureRandom.uuid,
            count: measurements.count,
            site_name: current_site.name,
            timestamp: batch_data[:timestamp]
          }

          render json: MeasurementBatchSerializer.new(batch_result).serializable_hash,
                 status: :created
        else
          errors = measurements.flat_map { |m| m.errors.full_messages }
          render_jsonapi_errors(errors.uniq, status: :unprocessable_entity)
        end
      end

      # GET /api/v1/measurements
      # List measurements for the current site
      def index
        measurements = current_site.measurements
                                   .order(timestamp: :desc)
                                   .limit(params[:limit] || 100)

        measurements = measurements.for_host(params[:host]) if params[:host].present?
        measurements = measurements.recent(params[:since].to_i.minutes.ago) if params[:since].present?

        render json: MeasurementSerializer.new(measurements).serializable_hash
      end

      private

      def build_measurements(batch_data)
        batch_data[:measurements].map do |m|
          current_site.measurements.build(
            host: m[:host],
            ip: m[:ip],
            timestamp: batch_data[:timestamp],
            latency_ms: m[:latency_ms],
            packet_loss: m[:packet_loss],
            jitter_ms: m[:jitter_ms],
            is_up: m[:is_up]
          )
        end
      end

      def measurement_params
        attrs = params.require(:data).require(:attributes)
        attrs.permit(
          :site,
          :timestamp,
          measurements: [:host, :ip, :latency_ms, :packet_loss, :jitter_ms, :is_up]
        )
      end
    end
  end
end
