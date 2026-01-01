class SiteHealthCheckJob < ApplicationJob
  queue_as :default

  OFFLINE_THRESHOLD = 5.minutes

  def perform
    Rails.logger.info "[SiteHealthCheckJob] Checking health of all sites"

    Site.find_each do |site|
      check_site_health(site)
    end

    Rails.logger.info "[SiteHealthCheckJob] Completed site health check"
  end

  private

  def check_site_health(site)
    if site_offline?(site)
      handle_offline_site(site)
    else
      handle_online_site(site)
    end
  end

  def site_offline?(site)
    site.last_heartbeat.nil? || site.last_heartbeat < OFFLINE_THRESHOLD.ago
  end

  def handle_offline_site(site)
    unless active_site_offline_anomaly?(site)
      create_site_offline_anomaly(site)
    end
    site.update!(status: "offline")
  end

  def handle_online_site(site)
    resolve_site_offline_anomaly(site)
    update_site_status_from_anomalies(site)
  end

  def active_site_offline_anomaly?(site)
    site.anomalies.where(anomaly_type: :site_offline).active.exists?
  end

  def create_site_offline_anomaly(site)
    site.anomalies.create!(
      anomaly_type: :site_offline,
      severity: :critical,
      message: "Site #{site.name} has stopped reporting",
      context_snapshot: {
        last_heartbeat: site.last_heartbeat,
        detected_at: Time.current
      }
    )

    Rails.logger.warn "[SiteHealthCheckJob] Site #{site.name} marked offline - no heartbeat since #{site.last_heartbeat}"
  end

  def resolve_site_offline_anomaly(site)
    site.anomalies
        .where(anomaly_type: :site_offline)
        .active
        .find_each(&:resolve!)
  end

  def update_site_status_from_anomalies(site)
    status = if site.anomalies.active.critical.exists?
               "critical"
    elsif site.anomalies.active.where(severity: :warning).exists?
               "warning"
    else
               "healthy"
    end

    site.update!(status: status)
  end
end
