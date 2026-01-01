require "rails_helper"

RSpec.describe Baseline, type: :model do
  describe "associations" do
    it { should belong_to(:site) }
  end

  describe "validations" do
    subject { build(:baseline) }

    it { should validate_presence_of(:host) }
    it { should validate_presence_of(:ip) }
    it { should validate_presence_of(:window_start) }
    it { should validate_presence_of(:window_end) }

    it "validates uniqueness of host scoped to site" do
      site = create(:site)
      create(:baseline, site: site, host: "router")

      duplicate = build(:baseline, site: site, host: "router")
      expect(duplicate).not_to be_valid
      expect(duplicate.errors[:host]).to include("has already been taken")
    end

    it "allows same host for different sites" do
      site1 = create(:site)
      site2 = create(:site)
      create(:baseline, site: site1, host: "router")

      different_site = build(:baseline, site: site2, host: "router")
      expect(different_site).to be_valid
    end
  end

  describe "factory" do
    it "creates valid baseline" do
      baseline = build(:baseline)
      expect(baseline).to be_valid
    end

    it "has sensible default values" do
      baseline = build(:baseline)
      expect(baseline.latency_mean).to eq(25.0)
      expect(baseline.latency_stddev).to eq(5.0)
      expect(baseline.latency_p95).to eq(35.0)
      expect(baseline.latency_p99).to eq(50.0)
      expect(baseline.sample_count).to eq(100)
    end
  end
end
