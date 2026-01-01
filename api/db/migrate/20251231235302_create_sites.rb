class CreateSites < ActiveRecord::Migration[8.1]
  def change
    create_table :sites do |t|
      t.string :name
      t.string :secret_digest
      t.datetime :last_heartbeat
      t.string :status
      t.json :topology_data

      t.timestamps
    end
    add_index :sites, :name, unique: true
  end
end
