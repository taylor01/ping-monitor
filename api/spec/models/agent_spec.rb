require "rails_helper"

RSpec.describe Agent, type: :model do
  describe "validations" do
    subject { build(:agent) }

    it { should validate_presence_of(:name) }
    it { should validate_uniqueness_of(:name) }
  end

  describe "#can_authenticate?" do
    context "with active status" do
      let(:agent) { build(:agent, status: :active) }

      it "returns true" do
        expect(agent.can_authenticate?).to be true
      end
    end

    context "with suspended status" do
      let(:agent) { build(:agent, :suspended) }

      it "returns false" do
        expect(agent.can_authenticate?).to be false
      end
    end

    context "with deactivated status" do
      let(:agent) { build(:agent, :deactivated) }

      it "returns false" do
        expect(agent.can_authenticate?).to be false
      end
    end
  end

  describe "#available_scopes" do
    let(:agent) { build(:agent) }

    it "returns standard agent scopes" do
      expect(agent.available_scopes).to eq(%w[sites:read anomalies:read anomalies:write])
    end
  end

  describe "#validate_scopes" do
    let(:agent) { build(:agent) }

    it "filters requested scopes to available ones" do
      result = agent.validate_scopes(%w[sites:read sites:write anomalies:read])
      expect(result).to eq(%w[sites:read anomalies:read])
    end

    it "returns available_scopes when blank" do
      expect(agent.validate_scopes(nil)).to eq(agent.available_scopes)
      expect(agent.validate_scopes([])).to eq(agent.available_scopes)
    end
  end

  describe "status enum" do
    it "defaults to active" do
      agent = Agent.new(name: "test", secret: "secret")
      expect(agent.status).to eq("active")
    end

    it "supports active, suspended, and deactivated statuses" do
      %w[active suspended deactivated].each do |status|
        agent = build(:agent, status: status)
        expect(agent.status).to eq(status)
      end
    end
  end
end
