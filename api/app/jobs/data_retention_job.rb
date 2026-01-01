class DataRetentionJob < ApplicationJob
  queue_as :default

  MEASUREMENT_RETENTION_DAYS = 7

  def perform
    Rails.logger.info "[DataRetentionJob] Starting data retention cleanup"

    deleted_count = prune_old_measurements

    Rails.logger.info "[DataRetentionJob] Completed - deleted #{deleted_count} old measurements"
  end

  private

  def prune_old_measurements
    cutoff = MEASUREMENT_RETENTION_DAYS.days.ago

    # Delete old measurements in batches to avoid locking
    total_deleted = 0

    loop do
      deleted = Measurement.where("timestamp < ?", cutoff).limit(1000).delete_all
      total_deleted += deleted
      break if deleted == 0

      # Small pause to reduce database load
      sleep(0.1)
    end

    total_deleted
  end
end
