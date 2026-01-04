require "rails_helper"

RSpec.describe ApiClient, type: :model do
  describe "validations" do
    subject { build(:api_client) }

    it { should validate_presence_of(:name) }
    it { should validate_uniqueness_of(:client_id) }
    # Note: client_id presence is validated but auto-generated before validation
  end

  describe "#can_authenticate?" do
    context "with active status" do
      let(:api_client) { build(:api_client, status: :active) }

      it "returns true" do
        expect(api_client.can_authenticate?).to be true
      end
    end

    context "with suspended status" do
      let(:api_client) { build(:api_client, :suspended) }

      it "returns false" do
        expect(api_client.can_authenticate?).to be false
      end
    end

    context "with deactivated status" do
      let(:api_client) { build(:api_client, :deactivated) }

      it "returns false" do
        expect(api_client.can_authenticate?).to be false
      end
    end
  end

  describe "#available_scopes" do
    it "returns allowed_scopes from database" do
      api_client = build(:api_client, allowed_scopes: %w[sites:read anomalies:read])
      expect(api_client.available_scopes).to eq(%w[sites:read anomalies:read])
    end

    it "returns empty array when allowed_scopes is nil" do
      api_client = build(:api_client, allowed_scopes: nil)
      expect(api_client.available_scopes).to eq([])
    end
  end

  describe "#validate_scopes" do
    let(:api_client) { build(:api_client, allowed_scopes: %w[sites:read anomalies:read]) }

    it "filters requested scopes to available ones" do
      result = api_client.validate_scopes(%w[sites:read sites:write anomalies:read])
      expect(result).to eq(%w[sites:read anomalies:read])
    end

    it "returns available_scopes when blank" do
      expect(api_client.validate_scopes(nil)).to eq(api_client.available_scopes)
      expect(api_client.validate_scopes([])).to eq(api_client.available_scopes)
    end

    context "with wildcard scope" do
      let(:api_client) { build(:api_client, :full_access) }

      it "returns wildcard for any request" do
        result = api_client.validate_scopes(%w[anything:here])
        expect(result).to eq(%w[*])
      end
    end
  end

  describe "client_id generation" do
    it "auto-generates client_id on create" do
      api_client = ApiClient.new(name: "test", secret: "secret")
      api_client.valid?
      expect(api_client.client_id).to match(/\Aac_[a-f0-9]{32}\z/)
    end

    it "does not override provided client_id" do
      api_client = ApiClient.new(name: "test", secret: "secret", client_id: "ac_custom123")
      api_client.valid?
      expect(api_client.client_id).to eq("ac_custom123")
    end
  end

  describe "status enum" do
    it "defaults to active" do
      api_client = ApiClient.new(name: "test", secret: "secret")
      expect(api_client.status).to eq("active")
    end

    it "supports active, suspended, and deactivated statuses" do
      %w[active suspended deactivated].each do |status|
        api_client = build(:api_client, status: status)
        expect(api_client.status).to eq(status)
      end
    end
  end
end
