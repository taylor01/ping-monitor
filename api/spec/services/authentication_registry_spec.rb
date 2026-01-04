require "rails_helper"

RSpec.describe AuthenticationRegistry do
  describe ".authenticate" do
    context "with type: 'site'" do
      let!(:site) { create(:site, name: "test-site") }

      it "authenticates with valid name and secret" do
        result = described_class.authenticate(
          type: "site",
          identifier: "test-site",
          secret: "test-secret-123"
        )
        expect(result).to eq(site)
      end

      it "returns nil with wrong secret" do
        result = described_class.authenticate(
          type: "site",
          identifier: "test-site",
          secret: "wrong-secret"
        )
        expect(result).to be_nil
      end

      it "returns nil with non-existent site" do
        result = described_class.authenticate(
          type: "site",
          identifier: "non-existent",
          secret: "test-secret-123"
        )
        expect(result).to be_nil
      end
    end

    context "with type: 'user'" do
      let!(:user) { create(:user, email: "test@example.com", password: "password123") }

      it "authenticates with valid email and password" do
        result = described_class.authenticate(
          type: "user",
          identifier: "test@example.com",
          secret: "password123"
        )
        expect(result).to eq(user)
      end

      it "returns nil with wrong password" do
        result = described_class.authenticate(
          type: "user",
          identifier: "test@example.com",
          secret: "wrong-password"
        )
        expect(result).to be_nil
      end

      it "returns nil with non-existent email" do
        result = described_class.authenticate(
          type: "user",
          identifier: "nonexistent@example.com",
          secret: "password123"
        )
        expect(result).to be_nil
      end
    end

    context "with type: 'agent'" do
      let!(:agent) { create(:agent, name: "test-agent") }

      it "authenticates with valid name and secret" do
        result = described_class.authenticate(
          type: "agent",
          identifier: "test-agent",
          secret: "agent-secret-123"
        )
        expect(result).to eq(agent)
      end

      it "returns nil with wrong secret" do
        result = described_class.authenticate(
          type: "agent",
          identifier: "test-agent",
          secret: "wrong-secret"
        )
        expect(result).to be_nil
      end

      it "returns nil with non-existent agent" do
        result = described_class.authenticate(
          type: "agent",
          identifier: "non-existent",
          secret: "agent-secret-123"
        )
        expect(result).to be_nil
      end
    end

    context "with type: 'api_client'" do
      let!(:api_client) { create(:api_client, name: "test-client") }

      it "authenticates with valid client_id and secret" do
        result = described_class.authenticate(
          type: "api_client",
          identifier: api_client.client_id,
          secret: "client-secret-123"
        )
        expect(result).to eq(api_client)
      end

      it "returns nil with wrong secret" do
        result = described_class.authenticate(
          type: "api_client",
          identifier: api_client.client_id,
          secret: "wrong-secret"
        )
        expect(result).to be_nil
      end

      it "returns nil with non-existent client_id" do
        result = described_class.authenticate(
          type: "api_client",
          identifier: "ac_nonexistent",
          secret: "client-secret-123"
        )
        expect(result).to be_nil
      end
    end

    context "with unsupported type" do
      it "returns nil for unknown type" do
        result = described_class.authenticate(
          type: "unknown",
          identifier: "test",
          secret: "secret"
        )
        expect(result).to be_nil
      end
    end

    context "with case-insensitive type" do
      let!(:site) { create(:site, name: "test-site") }

      it "handles uppercase type" do
        result = described_class.authenticate(
          type: "SITE",
          identifier: "test-site",
          secret: "test-secret-123"
        )
        expect(result).to eq(site)
      end

      it "handles mixed case type" do
        result = described_class.authenticate(
          type: "Site",
          identifier: "test-site",
          secret: "test-secret-123"
        )
        expect(result).to eq(site)
      end
    end

    context "with nil/blank parameters" do
      it "returns nil with nil type" do
        result = described_class.authenticate(
          type: nil,
          identifier: "test",
          secret: "secret"
        )
        expect(result).to be_nil
      end

      it "returns nil with blank identifier" do
        result = described_class.authenticate(
          type: "site",
          identifier: "",
          secret: "secret"
        )
        expect(result).to be_nil
      end

      it "returns nil with nil secret" do
        result = described_class.authenticate(
          type: "site",
          identifier: "test",
          secret: nil
        )
        expect(result).to be_nil
      end
    end
  end

  describe ".supported_types" do
    it "returns all supported types" do
      expect(described_class.supported_types).to contain_exactly("site", "user", "agent", "api_client")
    end
  end

  describe ".supports?" do
    it "returns true for valid types" do
      %w[site user agent api_client].each do |type|
        expect(described_class.supports?(type)).to be true
      end
    end

    it "returns true for uppercase types" do
      expect(described_class.supports?("SITE")).to be true
    end

    it "returns false for invalid types" do
      expect(described_class.supports?("invalid")).to be false
      expect(described_class.supports?("")).to be false
      expect(described_class.supports?(nil)).to be false
    end
  end
end
