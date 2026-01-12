class CreateIncidents < ActiveRecord::Migration[8.1]
  def change
    create_table :incidents do |t|
      t.references :site, null: false, foreign_key: true
      t.datetime :started_at, null: false
      t.datetime :resolved_at
      t.boolean :auto_recovered, default: false
      t.text :nc_summary
      t.text :nc_root_cause_guess
      t.jsonb :devices_affected, default: []
      t.text :human_root_cause
      t.text :human_notes
      t.datetime :human_reviewed_at
      t.string :severity, default: "normal"
      t.boolean :reported_in_summary, default: false

      t.timestamps
    end

    add_index :incidents, :started_at
    add_index :incidents, :resolved_at
    add_index :incidents, :updated_at
    add_index :incidents, :human_reviewed_at
    add_index :incidents, :reported_in_summary
    add_index :incidents, [ :site_id, :resolved_at ]
  end
end
