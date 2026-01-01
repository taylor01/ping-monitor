class AnalysisLog < ApplicationRecord
  # Associations
  belongs_to :anomaly

  # Validations
  validates :trigger_type, presence: true
  validates :claude_model, presence: true

  # Methods
  def total_tokens
    (prompt_tokens || 0) + (completion_tokens || 0)
  end
end
