class CreateInferredTopologies < ActiveRecord::Migration[8.1]
  def change
    create_table :inferred_topologies do |t|
      t.references :site, null: false, foreign_key: true
      t.string :upstream_device, null: false
      t.string :downstream_device, null: false
      t.float :confidence, default: 0.5
      t.integer :observed_count, default: 1
      t.datetime :last_seen_at

      t.timestamps
    end

    add_index :inferred_topologies, [ :site_id, :upstream_device, :downstream_device ],
              unique: true, name: "idx_topology_unique"
    add_index :inferred_topologies, [ :site_id, :upstream_device ]
    add_index :inferred_topologies, :confidence
  end
end
