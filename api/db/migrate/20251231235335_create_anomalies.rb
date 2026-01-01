class CreateAnomalies < ActiveRecord::Migration[8.1]
  def change
    create_table :anomalies do |t|
      t.references :site, null: false, foreign_key: true
      t.references :measurement, foreign_key: true  # Optional - not all anomalies have a measurement
      t.string :host
      t.integer :anomaly_type, null: false
      t.integer :severity, null: false
      t.float :current_value
      t.float :baseline_value
      t.text :message
      t.json :context_snapshot
      t.datetime :resolved_at

      t.timestamps
    end

    add_index :anomalies, [:site_id, :created_at]
    add_index :anomalies, :resolved_at
    add_index :anomalies, [:severity, :created_at], where: "resolved_at IS NULL", name: "index_active_anomalies_by_severity"
  end
end
