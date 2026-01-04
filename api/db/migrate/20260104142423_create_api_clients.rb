class CreateApiClients < ActiveRecord::Migration[8.1]
  def change
    create_table :api_clients do |t|
      t.string :name, null: false
      t.string :client_id, null: false
      t.string :secret_digest
      t.string :description
      t.string :status, default: "active"
      t.json :allowed_scopes, default: []

      t.timestamps
    end
    add_index :api_clients, :client_id, unique: true
  end
end
