require "rails_helper"

RSpec.describe MeasurementPolicy do
  let(:site) { create(:site) }
  let(:other_site) { create(:site) }
  let(:measurement) { create(:measurement, site: site) }
  let(:other_measurement) { create(:measurement, site: other_site) }
  let(:user) { create(:user) }
  let(:agent) { create(:agent) }
  let(:api_client) { create(:api_client) }

  describe "#index?" do
    it "allows all authenticatable types" do
      expect(described_class.new(site, Measurement).index?).to be true
      expect(described_class.new(user, Measurement).index?).to be true
      expect(described_class.new(agent, Measurement).index?).to be true
      expect(described_class.new(api_client, Measurement).index?).to be true
    end
  end

  describe "#show?" do
    context "when authenticatable is a Site" do
      it "allows viewing own measurements" do
        expect(described_class.new(site, measurement).show?).to be true
      end

      it "denies viewing other sites' measurements" do
        expect(described_class.new(site, other_measurement).show?).to be false
      end
    end

    context "when authenticatable is a User" do
      it "allows viewing any measurement" do
        expect(described_class.new(user, measurement).show?).to be true
        expect(described_class.new(user, other_measurement).show?).to be true
      end
    end

    context "when authenticatable is an Agent" do
      it "allows viewing any measurement" do
        expect(described_class.new(agent, measurement).show?).to be true
        expect(described_class.new(agent, other_measurement).show?).to be true
      end
    end

    context "when authenticatable is an ApiClient" do
      it "allows viewing any measurement" do
        expect(described_class.new(api_client, measurement).show?).to be true
        expect(described_class.new(api_client, other_measurement).show?).to be true
      end
    end
  end

  describe "#create?" do
    it "allows Sites to create measurements" do
      expect(described_class.new(site, Measurement).create?).to be true
    end

    it "denies Users from creating measurements" do
      expect(described_class.new(user, Measurement).create?).to be false
    end

    it "denies Agents from creating measurements" do
      expect(described_class.new(agent, Measurement).create?).to be false
    end

    it "denies ApiClients from creating measurements" do
      expect(described_class.new(api_client, Measurement).create?).to be false
    end
  end

  describe MeasurementPolicy::Scope do
    let!(:site_measurement) { create(:measurement, site: site) }
    let!(:other_site_measurement) { create(:measurement, site: other_site) }

    describe "#resolve" do
      context "when authenticatable is a Site" do
        it "returns only the site's measurements" do
          scope = described_class.new(site, Measurement.all).resolve
          expect(scope).to include(site_measurement)
          expect(scope).not_to include(other_site_measurement)
        end
      end

      context "when authenticatable is a User" do
        it "returns all measurements" do
          scope = described_class.new(user, Measurement.all).resolve
          expect(scope).to include(site_measurement, other_site_measurement)
        end
      end

      context "when authenticatable is an Agent" do
        it "returns all measurements" do
          scope = described_class.new(agent, Measurement.all).resolve
          expect(scope).to include(site_measurement, other_site_measurement)
        end
      end

      context "when authenticatable is an ApiClient" do
        it "returns all measurements" do
          scope = described_class.new(api_client, Measurement.all).resolve
          expect(scope).to include(site_measurement, other_site_measurement)
        end
      end
    end
  end
end
