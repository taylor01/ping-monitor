class AnomalyDetectionService
  LATENCY_WARNING_THRESHOLD = 1.5   # > p95 * 1.5 = warning
  LATENCY_CRITICAL_THRESHOLD = 2.0  # > p95 * 2.0 = critical
  PACKET_LOSS_WARNING = 10          # > 10% loss = warning
  PACKET_LOSS_CRITICAL = 50         # > 50% loss = critical

  class << self
    def detect_for_batch(measurements)
      return if measurements.empty?

      # Preload all baselines for the site to avoid N+1 queries
      site = measurements.first.site
      baselines_by_host = site.baselines.index_by(&:host)

      measurements.each do |measurement|
        baseline = baselines_by_host[measurement.host]
        detect_for_measurement(measurement, baseline)
      end
    end

    def detect_for_measurement(measurement, baseline = nil)
      # Look up baseline if not provided (for direct calls)
      baseline ||= measurement.site.baselines.find_by(host: measurement.host)

      # Cold start: skip detection if no baseline exists yet
      return if baseline.nil?

      detect_host_status_change(measurement, baseline)

      if measurement.is_up
        detect_latency_anomaly(measurement, baseline)
        detect_packet_loss_anomaly(measurement, baseline)
      end
    end

    private

    def detect_host_status_change(measurement, baseline)
      if !measurement.is_up
        create_host_down_anomaly(measurement, baseline)
      else
        resolve_host_down_anomaly(measurement)
      end
    end

    def create_host_down_anomaly(measurement, baseline)
      # Don't create duplicate if there's already an active host_down anomaly
      return if active_anomaly_exists?(measurement.site, measurement.host, :host_down)

      measurement.site.anomalies.create!(
        host: measurement.host,
        measurement: measurement,
        anomaly_type: :host_down,
        severity: :critical,
        message: "Host #{measurement.host} is unreachable",
        current_value: 0,
        baseline_value: baseline&.sample_count,
        context_snapshot: build_context_snapshot(measurement, baseline)
      )
    end

    def resolve_host_down_anomaly(measurement)
      active_anomaly = measurement.site.anomalies
                                  .where(host: measurement.host, anomaly_type: :host_down)
                                  .active
                                  .first

      return unless active_anomaly

      active_anomaly.resolve!

      # Create recovery anomaly for tracking
      measurement.site.anomalies.create!(
        host: measurement.host,
        measurement: measurement,
        anomaly_type: :host_recovery,
        severity: :info,
        message: "Host #{measurement.host} has recovered",
        context_snapshot: { resolved_anomaly_id: active_anomaly.id }
      )
    end

    def detect_latency_anomaly(measurement, baseline)
      return if measurement.latency_ms.nil?
      return if baseline.latency_p95.nil?

      latency = measurement.latency_ms
      p95 = baseline.latency_p95

      if latency > p95 * LATENCY_CRITICAL_THRESHOLD
        create_latency_anomaly(measurement, baseline, :critical)
      elsif latency > p95 * LATENCY_WARNING_THRESHOLD
        create_latency_anomaly(measurement, baseline, :warning)
      else
        # Latency is normal - resolve any active latency anomalies
        resolve_latency_anomaly(measurement)
      end
    end

    def create_latency_anomaly(measurement, baseline, severity)
      # Don't create duplicate if there's already an active latency_spike anomaly
      return if active_anomaly_exists?(measurement.site, measurement.host, :latency_spike)

      measurement.site.anomalies.create!(
        host: measurement.host,
        measurement: measurement,
        anomaly_type: :latency_spike,
        severity: severity,
        message: "Latency spike on #{measurement.host}: #{measurement.latency_ms.round(1)}ms (baseline p95: #{baseline.latency_p95.round(1)}ms)",
        current_value: measurement.latency_ms,
        baseline_value: baseline.latency_p95,
        context_snapshot: build_context_snapshot(measurement, baseline)
      )
    end

    def resolve_latency_anomaly(measurement)
      measurement.site.anomalies
                 .where(host: measurement.host, anomaly_type: :latency_spike)
                 .active
                 .find_each(&:resolve!)
    end

    def detect_packet_loss_anomaly(measurement, baseline)
      return if measurement.packet_loss.nil?

      loss = measurement.packet_loss

      if loss > PACKET_LOSS_CRITICAL
        create_packet_loss_anomaly(measurement, baseline, :critical)
      elsif loss > PACKET_LOSS_WARNING
        create_packet_loss_anomaly(measurement, baseline, :warning)
      else
        resolve_packet_loss_anomaly(measurement)
      end
    end

    def create_packet_loss_anomaly(measurement, baseline, severity)
      return if active_anomaly_exists?(measurement.site, measurement.host, :packet_loss)

      measurement.site.anomalies.create!(
        host: measurement.host,
        measurement: measurement,
        anomaly_type: :packet_loss,
        severity: severity,
        message: "Packet loss on #{measurement.host}: #{measurement.packet_loss.round(1)}%",
        current_value: measurement.packet_loss,
        baseline_value: 0,
        context_snapshot: build_context_snapshot(measurement, baseline)
      )
    end

    def resolve_packet_loss_anomaly(measurement)
      measurement.site.anomalies
                 .where(host: measurement.host, anomaly_type: :packet_loss)
                 .active
                 .find_each(&:resolve!)
    end

    def active_anomaly_exists?(site, host, anomaly_type)
      site.anomalies
          .where(host: host, anomaly_type: anomaly_type)
          .active
          .exists?
    end

    def build_context_snapshot(measurement, baseline)
      {
        measurement: {
          timestamp: measurement.timestamp,
          latency_ms: measurement.latency_ms,
          packet_loss: measurement.packet_loss,
          jitter_ms: measurement.jitter_ms,
          is_up: measurement.is_up
        },
        baseline: baseline ? {
          latency_mean: baseline.latency_mean,
          latency_stddev: baseline.latency_stddev,
          latency_p95: baseline.latency_p95,
          latency_p99: baseline.latency_p99,
          sample_count: baseline.sample_count
        } : nil
      }
    end
  end
end
