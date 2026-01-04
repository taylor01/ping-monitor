require "rails_helper"

RSpec.describe BaselinePolicy do
  let(:site) { create(:site) }
  let(:other_site) { create(:site) }
  let(:baseline) { create(:baseline, site: site) }
  let(:other_baseline) { create(:baseline, site: other_site) }
  let(:user) { create(:user) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe "#index?" do
    it "allows all authenticatable types" do
      expect(described_class.new(site, Baseline).index?).to be true
      expect(described_class.new(user, Baseline).index?).to be true
      expect(described_class.new(agent, Baseline).index?).to be true
      expect(described_class.new(api_client, Baseline).index?).to be true
    end
  end

  describe "#show?" do
    context "when authenticatable is a Site" do
      it "allows viewing own baselines" do
        expect(described_class.new(site, baseline).show?).to be true
      end

      it "denies viewing other sites' baselines" do
        expect(described_class.new(site, other_baseline).show?).to be false
      end
    end

    context "when authenticatable is a User" do
      it "allows viewing any baseline" do
        expect(described_class.new(user, baseline).show?).to be true
        expect(described_class.new(user, other_baseline).show?).to be true
      end
    end

    context "when authenticatable is an Agent" do
      it "allows viewing any baseline" do
        expect(described_class.new(agent, baseline).show?).to be true
        expect(described_class.new(agent, other_baseline).show?).to be true
      end
    end

    context "when authenticatable is an ApiClient" do
      it "allows viewing any baseline" do
        expect(described_class.new(api_client, baseline).show?).to be true
        expect(described_class.new(api_client, other_baseline).show?).to be true
      end
    end
  end

  describe BaselinePolicy::Scope do
    let!(:site_baseline) { create(:baseline, site: site) }
    let!(:other_site_baseline) { create(:baseline, site: other_site) }

    describe "#resolve" do
      context "when authenticatable is a Site" do
        it "returns only the site's baselines" do
          scope = described_class.new(site, Baseline.all).resolve
          expect(scope).to include(site_baseline)
          expect(scope).not_to include(other_site_baseline)
        end
      end

      context "when authenticatable is a User" do
        it "returns all baselines" do
          scope = described_class.new(user, Baseline.all).resolve
          expect(scope).to include(site_baseline, other_site_baseline)
        end
      end

      context "when authenticatable is an Agent" do
        it "returns all baselines" do
          scope = described_class.new(agent, Baseline.all).resolve
          expect(scope).to include(site_baseline, other_site_baseline)
        end
      end

      context "when authenticatable is an ApiClient" do
        it "returns all baselines" do
          scope = described_class.new(api_client, Baseline.all).resolve
          expect(scope).to include(site_baseline, other_site_baseline)
        end
      end
    end
  end
end
