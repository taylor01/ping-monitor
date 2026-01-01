class BaselineCalculationService
  WINDOW_HOURS = 168  # 7 days
  MIN_SAMPLES = 60    # ~1 hour of data at 60s intervals

  class << self
    def calculate_for_site(site)
      window_start = WINDOW_HOURS.hours.ago
      window_end = Time.current

      # Get unique hosts with measurements in window
      hosts = site.measurements
                  .where("timestamp > ?", window_start)
                  .distinct
                  .pluck(:host, :ip)

      hosts.each do |host, ip|
        calculate_for_host(site, host, ip, window_start, window_end)
      end
    end

    def calculate_for_host(site, host, ip, window_start, window_end)
      measurements = site.measurements
                         .where(host: host)
                         .where("timestamp > ?", window_start)
                         .where(is_up: true)
                         .pluck(:latency_ms)
                         .compact

      return if measurements.size < MIN_SAMPLES

      stats = calculate_stats(measurements)

      site.baselines.find_or_initialize_by(host: host).tap do |baseline|
        baseline.assign_attributes(
          ip: ip,
          latency_mean: stats[:mean],
          latency_stddev: stats[:stddev],
          latency_p95: stats[:p95],
          latency_p99: stats[:p99],
          sample_count: measurements.size,
          window_start: window_start,
          window_end: window_end
        )
        baseline.save!
      end
    end

    def calculate_stats(latencies)
      return {} if latencies.empty?

      sorted = latencies.sort
      n = sorted.size

      mean = sorted.sum / n.to_f
      variance = sorted.map { |x| (x - mean)**2 }.sum / n.to_f
      stddev = Math.sqrt(variance)

      {
        mean: mean.round(3),
        stddev: stddev.round(3),
        p95: percentile(sorted, 95).round(3),
        p99: percentile(sorted, 99).round(3)
      }
    end

    def percentile(sorted_array, p)
      return sorted_array.first if sorted_array.size == 1

      rank = (p / 100.0) * (sorted_array.size - 1)
      lower = sorted_array[rank.floor]
      upper = sorted_array[rank.ceil]

      lower + (upper - lower) * (rank - rank.floor)
    end
  end
end
