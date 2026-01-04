class CreateUsers < ActiveRecord::Migration[8.1]
  def change
    create_table :users do |t|
      t.string :email, null: false
      t.string :password_digest
      t.string :name
      t.string :role, default: "viewer"

      t.timestamps
    end
    add_index :users, :email, unique: true
  end
end
