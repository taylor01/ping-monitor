class CreateBaselines < ActiveRecord::Migration[8.1]
  def change
    create_table :baselines do |t|
      t.references :site, null: false, foreign_key: true
      t.string :host, null: false
      t.string :ip
      t.float :latency_mean
      t.float :latency_stddev
      t.float :latency_p95
      t.float :latency_p99
      t.integer :sample_count, default: 0
      t.datetime :window_start
      t.datetime :window_end

      t.timestamps
    end

    add_index :baselines, [ :site_id, :host ], unique: true
  end
end
