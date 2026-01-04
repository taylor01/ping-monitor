require "rails_helper"

RSpec.describe TokenAuthenticatable do
  # Test shared behavior using Site as the implementing model
  let(:site) { create(:site) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe "#authenticate_secret" do
    it "returns truthy for correct secret" do
      expect(site.authenticate_secret("test-secret-123")).to be_truthy
    end

    it "returns falsy for incorrect secret" do
      expect(site.authenticate_secret("wrong-secret")).to be_falsy
    end

    it "returns falsy for nil secret" do
      expect(site.authenticate_secret(nil)).to be_falsy
    end

    it "returns falsy for empty secret" do
      expect(site.authenticate_secret("")).to be_falsy
    end
  end

  describe "#available_scopes" do
    it "is implemented by Site" do
      expect(site.available_scopes).to eq(%w[sites:read sites:write measurements:write anomalies:read])
    end

    it "is implemented by Agent" do
      expect(agent.available_scopes).to eq(%w[sites:read anomalies:read anomalies:write])
    end

    it "is implemented by ApiClient" do
      expect(api_client.available_scopes).to eq(api_client.allowed_scopes)
    end
  end

  describe "#can_authenticate?" do
    context "for Site" do
      it "returns true (Sites are always authenticatable)" do
        expect(site.can_authenticate?).to be true
      end
    end

    context "for Agent" do
      it "returns true when active" do
        agent.status = :active
        expect(agent.can_authenticate?).to be true
      end

      it "returns false when suspended" do
        agent.status = :suspended
        expect(agent.can_authenticate?).to be false
      end

      it "returns false when deactivated" do
        agent.status = :deactivated
        expect(agent.can_authenticate?).to be false
      end
    end

    context "for ApiClient" do
      it "returns true when active" do
        api_client.status = :active
        expect(api_client.can_authenticate?).to be true
      end

      it "returns false when suspended" do
        api_client.status = :suspended
        expect(api_client.can_authenticate?).to be false
      end

      it "returns false when deactivated" do
        api_client.status = :deactivated
        expect(api_client.can_authenticate?).to be false
      end
    end
  end

  describe "#validate_scopes" do
    context "when requested_scopes is blank" do
      it "returns available_scopes" do
        expect(site.validate_scopes(nil)).to eq(site.available_scopes)
        expect(site.validate_scopes([])).to eq(site.available_scopes)
      end
    end

    context "when available_scopes includes wildcard" do
      let(:api_client) { create(:api_client, :full_access) }

      it "returns available_scopes (wildcard)" do
        expect(api_client.validate_scopes(%w[any:scope])).to eq(%w[*])
      end
    end

    context "with regular scopes" do
      it "returns intersection of requested and available" do
        result = site.validate_scopes(%w[sites:read sites:write admin:full])
        expect(result).to eq(%w[sites:read sites:write])
      end

      it "returns empty array when no overlap" do
        result = site.validate_scopes(%w[admin:full other:scope])
        expect(result).to eq([])
      end
    end
  end

  describe "secret hashing" do
    it "hashes the secret on creation" do
      new_site = Site.create!(name: "hashed-test", secret: "my-secret")
      expect(new_site.secret_digest).to be_present
      expect(new_site.secret_digest).not_to eq("my-secret")
    end

    it "can authenticate with the original secret" do
      new_site = Site.create!(name: "auth-test", secret: "original-secret")
      expect(new_site.authenticate_secret("original-secret")).to be_truthy
    end
  end
end
