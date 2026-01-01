class AnomalyDetectionJob < ApplicationJob
  queue_as :default

  def perform(measurement_ids)
    return if measurement_ids.blank?

    measurements = Measurement.where(id: measurement_ids).includes(:site)

    Rails.logger.info "[AnomalyDetectionJob] Processing #{measurements.size} measurements for anomaly detection"

    AnomalyDetectionService.detect_for_batch(measurements)

    Rails.logger.info "[AnomalyDetectionJob] Completed anomaly detection"
  end
end
