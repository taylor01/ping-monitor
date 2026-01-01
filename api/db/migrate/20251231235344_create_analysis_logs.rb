class CreateAnalysisLogs < ActiveRecord::Migration[8.1]
  def change
    create_table :analysis_logs do |t|
      t.references :anomaly, null: false, foreign_key: true
      t.string :trigger_type
      t.string :claude_model
      t.integer :prompt_tokens
      t.integer :completion_tokens
      t.text :analysis_text
      t.json :tool_calls
      t.json :recommended_actions

      t.timestamps
    end
  end
end
