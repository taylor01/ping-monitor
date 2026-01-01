class BaselineCalculationJob < ApplicationJob
  queue_as :default

  def perform
    Rails.logger.info "[BaselineCalculationJob] Starting baseline calculation for all sites"

    Site.find_each do |site|
      Rails.logger.info "[BaselineCalculationJob] Calculating baselines for site: #{site.name}"
      BaselineCalculationService.calculate_for_site(site)
    end

    Rails.logger.info "[BaselineCalculationJob] Completed baseline calculation"
  end
end
