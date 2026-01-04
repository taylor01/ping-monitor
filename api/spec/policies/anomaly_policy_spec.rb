require "rails_helper"

RSpec.describe AnomalyPolicy do
  let(:site) { create(:site) }
  let(:other_site) { create(:site) }
  let(:anomaly) { create(:anomaly, site: site) }
  let(:other_anomaly) { create(:anomaly, site: other_site) }
  let(:user_viewer) { create(:user, role: :viewer) }
  let(:user_operator) { create(:user, role: :operator) }
  let(:user_admin) { create(:user, role: :admin) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe "#index?" do
    it "allows all authenticatable types" do
      expect(described_class.new(site, Anomaly).index?).to be true
      expect(described_class.new(user_viewer, Anomaly).index?).to be true
      expect(described_class.new(agent, Anomaly).index?).to be true
      expect(described_class.new(api_client, Anomaly).index?).to be true
    end
  end

  describe "#show?" do
    context "when authenticatable is a Site" do
      it "allows viewing own anomalies" do
        expect(described_class.new(site, anomaly).show?).to be true
      end

      it "denies viewing other sites' anomalies" do
        expect(described_class.new(site, other_anomaly).show?).to be false
      end
    end

    context "when authenticatable is a User" do
      it "allows viewing any anomaly" do
        expect(described_class.new(user_viewer, anomaly).show?).to be true
        expect(described_class.new(user_viewer, other_anomaly).show?).to be true
      end
    end

    context "when authenticatable is an Agent" do
      it "allows viewing any anomaly" do
        expect(described_class.new(agent, anomaly).show?).to be true
        expect(described_class.new(agent, other_anomaly).show?).to be true
      end
    end

    context "when authenticatable is an ApiClient" do
      it "allows viewing any anomaly" do
        expect(described_class.new(api_client, anomaly).show?).to be true
        expect(described_class.new(api_client, other_anomaly).show?).to be true
      end
    end
  end

  describe "#resolve?" do
    context "when authenticatable is a Site" do
      it "allows resolving own anomalies" do
        expect(described_class.new(site, anomaly).resolve?).to be true
      end

      it "denies resolving other sites' anomalies" do
        expect(described_class.new(site, other_anomaly).resolve?).to be false
      end
    end

    context "when authenticatable is a User" do
      it "denies viewers from resolving" do
        expect(described_class.new(user_viewer, anomaly).resolve?).to be false
      end

      it "allows operators to resolve any anomaly" do
        expect(described_class.new(user_operator, anomaly).resolve?).to be true
        expect(described_class.new(user_operator, other_anomaly).resolve?).to be true
      end

      it "allows admins to resolve any anomaly" do
        expect(described_class.new(user_admin, anomaly).resolve?).to be true
        expect(described_class.new(user_admin, other_anomaly).resolve?).to be true
      end
    end

    context "when authenticatable is an Agent" do
      it "allows resolving any anomaly" do
        expect(described_class.new(agent, anomaly).resolve?).to be true
        expect(described_class.new(agent, other_anomaly).resolve?).to be true
      end
    end

    context "when authenticatable is an ApiClient" do
      it "denies resolving anomalies" do
        expect(described_class.new(api_client, anomaly).resolve?).to be false
      end
    end
  end

  describe "#history?" do
    it "allows all authenticatable types" do
      expect(described_class.new(site, Anomaly).history?).to be true
      expect(described_class.new(user_viewer, Anomaly).history?).to be true
      expect(described_class.new(agent, Anomaly).history?).to be true
      expect(described_class.new(api_client, Anomaly).history?).to be true
    end
  end

  describe AnomalyPolicy::Scope do
    let!(:site_anomaly) { create(:anomaly, site: site) }
    let!(:other_site_anomaly) { create(:anomaly, site: other_site) }

    describe "#resolve" do
      context "when authenticatable is a Site" do
        it "returns only the site's anomalies" do
          scope = described_class.new(site, Anomaly.all).resolve
          expect(scope).to include(site_anomaly)
          expect(scope).not_to include(other_site_anomaly)
        end
      end

      context "when authenticatable is a User" do
        it "returns all anomalies" do
          scope = described_class.new(user_viewer, Anomaly.all).resolve
          expect(scope).to include(site_anomaly, other_site_anomaly)
        end
      end

      context "when authenticatable is an Agent" do
        it "returns all anomalies" do
          scope = described_class.new(agent, Anomaly.all).resolve
          expect(scope).to include(site_anomaly, other_site_anomaly)
        end
      end

      context "when authenticatable is an ApiClient" do
        it "returns all anomalies" do
          scope = described_class.new(api_client, Anomaly.all).resolve
          expect(scope).to include(site_anomaly, other_site_anomaly)
        end
      end
    end
  end
end
