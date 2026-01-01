class CreateMeasurements < ActiveRecord::Migration[8.1]
  def change
    create_table :measurements do |t|
      t.references :site, null: false, foreign_key: true
      t.string :host, null: false
      t.string :ip, null: false
      t.datetime :timestamp, null: false
      t.float :latency_ms
      t.float :packet_loss
      t.float :jitter_ms
      t.boolean :is_up, null: false

      t.timestamps
    end

    add_index :measurements, [ :site_id, :host, :timestamp ]
    add_index :measurements, [ :site_id, :timestamp ]
    add_index :measurements, :timestamp
  end
end
