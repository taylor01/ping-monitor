class CreateAgents < ActiveRecord::Migration[8.1]
  def change
    create_table :agents do |t|
      t.string :name, null: false
      t.string :secret_digest
      t.string :description
      t.string :status, default: "active"
      t.datetime :last_activity_at

      t.timestamps
    end
    add_index :agents, :name, unique: true
  end
end
