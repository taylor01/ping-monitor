class CreateLearnedPatterns < ActiveRecord::Migration[8.1]
  def change
    create_table :learned_patterns do |t|
      t.references :site, null: false, foreign_key: true
      t.string :device
      t.string :pattern_type, null: false
      t.text :description
      t.float :confidence, default: 0.5
      t.integer :occurrences, default: 1
      t.string :time_pattern
      t.datetime :last_seen_at

      t.timestamps
    end

    add_index :learned_patterns, [ :site_id, :device, :pattern_type ], unique: true
    add_index :learned_patterns, :device
    add_index :learned_patterns, :confidence
  end
end
