class AddAnomalyIndexesForNcPolling < ActiveRecord::Migration[8.1]
  def change
    # Index for since filter (polling efficiency)
    add_index :anomalies, :updated_at

    # Composite index for history endpoint (site_id, host, created_at)
    add_index :anomalies, [ :site_id, :host, :created_at ], name: "index_anomalies_on_site_host_created"
  end
end
