require "rails_helper"

RSpec.describe SitePolicy do
  let(:site) { create(:site) }
  let(:other_site) { create(:site) }
  let(:user) { create(:user) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe "#index?" do
    it "allows Sites" do
      expect(described_class.new(site, Site).index?).to be true
    end

    it "allows Users" do
      expect(described_class.new(user, Site).index?).to be true
    end

    it "allows Agents" do
      expect(described_class.new(agent, Site).index?).to be true
    end

    it "allows ApiClients" do
      expect(described_class.new(api_client, Site).index?).to be true
    end
  end

  describe "#show?" do
    it "allows Sites to view any site" do
      expect(described_class.new(site, other_site).show?).to be true
    end

    it "allows Users to view any site" do
      expect(described_class.new(user, site).show?).to be true
    end

    it "allows Agents to view any site" do
      expect(described_class.new(agent, site).show?).to be true
    end

    it "allows ApiClients to view any site" do
      expect(described_class.new(api_client, site).show?).to be true
    end
  end

  describe "#me?" do
    it "allows Sites" do
      expect(described_class.new(site, site).me?).to be true
    end

    it "denies Users" do
      expect(described_class.new(user, site).me?).to be false
    end

    it "denies Agents" do
      expect(described_class.new(agent, site).me?).to be false
    end

    it "denies ApiClients" do
      expect(described_class.new(api_client, site).me?).to be false
    end
  end

  describe "#status?" do
    it "allows all authenticatable types" do
      expect(described_class.new(site, site).status?).to be true
      expect(described_class.new(user, site).status?).to be true
      expect(described_class.new(agent, site).status?).to be true
      expect(described_class.new(api_client, site).status?).to be true
    end
  end

  describe SitePolicy::Scope do
    let!(:site1) { create(:site) }
    let!(:site2) { create(:site) }

    describe "#resolve" do
      context "when authenticatable is a Site" do
        it "returns only the authenticated site" do
          scope = described_class.new(site1, Site.all).resolve
          expect(scope).to contain_exactly(site1)
          expect(scope).not_to include(site2)
        end
      end

      context "when authenticatable is a User" do
        it "returns all sites" do
          scope = described_class.new(user, Site.all).resolve
          expect(scope).to include(site1, site2)
        end
      end

      context "when authenticatable is an Agent" do
        it "returns all sites" do
          scope = described_class.new(agent, Site.all).resolve
          expect(scope).to include(site1, site2)
        end
      end

      context "when authenticatable is an ApiClient" do
        it "returns all sites" do
          scope = described_class.new(api_client, Site.all).resolve
          expect(scope).to include(site1, site2)
        end
      end
    end
  end
end
