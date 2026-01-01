require "rails_helper"

RSpec.describe AnalysisLog, type: :model do
  describe "associations" do
    it { should belong_to(:anomaly) }
  end

  describe "validations" do
    it { should validate_presence_of(:trigger_type) }
    it { should validate_presence_of(:claude_model) }
  end

  describe "factory" do
    it "creates valid analysis log" do
      analysis_log = build(:analysis_log)
      expect(analysis_log).to be_valid
    end

    it "has expected default values" do
      analysis_log = build(:analysis_log)
      expect(analysis_log.trigger_type).to eq("automatic")
      expect(analysis_log.claude_model).to eq("claude-sonnet-4-20250514")
      expect(analysis_log.prompt_tokens).to eq(500)
      expect(analysis_log.completion_tokens).to eq(200)
      expect(analysis_log.tool_calls).to eq([])
      expect(analysis_log.recommended_actions).to be_an(Array)
    end
  end
end
