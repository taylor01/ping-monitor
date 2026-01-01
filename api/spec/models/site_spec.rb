require "rails_helper"

RSpec.describe Site, type: :model do
  describe "associations" do
    it { should have_many(:measurements).dependent(:destroy) }
    it { should have_many(:baselines).dependent(:destroy) }
    it { should have_many(:anomalies).dependent(:destroy) }
  end

  describe "validations" do
    subject { build(:site) }

    it { should validate_presence_of(:name) }
    it { should validate_uniqueness_of(:name) }

    it "requires secret on create" do
      site = Site.new(name: "test-site")
      expect(site).not_to be_valid
      expect(site.errors[:secret]).to include("can't be blank")
    end

    it "does not require secret on update" do
      site = create(:site)
      site.secret = nil
      expect(site).to be_valid
    end
  end

  describe "enums" do
    it "defines status enum" do
      expect(Site.statuses).to eq({
        "unknown" => "unknown",
        "healthy" => "healthy",
        "warning" => "warning",
        "critical" => "critical",
        "offline" => "offline"
      })
    end

    it "defaults to unknown status" do
      site = Site.new(name: "test", secret: "secret")
      expect(site.status).to eq("unknown")
    end
  end

  describe "scopes" do
    describe ".online" do
      it "returns sites with recent heartbeat" do
        online_site = create(:site, last_heartbeat: 1.minute.ago)
        offline_site = create(:site, last_heartbeat: 10.minutes.ago)

        expect(Site.online).to include(online_site)
        expect(Site.online).not_to include(offline_site)
      end
    end

    describe ".offline" do
      it "returns sites with old or no heartbeat" do
        online_site = create(:site, last_heartbeat: 1.minute.ago)
        offline_site = create(:site, last_heartbeat: 10.minutes.ago)
        nil_heartbeat = create(:site, last_heartbeat: nil)

        expect(Site.offline).not_to include(online_site)
        expect(Site.offline).to include(offline_site)
        expect(Site.offline).to include(nil_heartbeat)
      end
    end
  end

  describe "#healthy?" do
    it "returns true for recent heartbeat" do
      site = build(:site, last_heartbeat: 1.minute.ago)
      expect(site.healthy?).to be true
    end

    it "returns false for old heartbeat" do
      site = build(:site, last_heartbeat: 10.minutes.ago)
      expect(site.healthy?).to be false
    end

    it "returns false for nil heartbeat" do
      site = build(:site, last_heartbeat: nil)
      expect(site.healthy?).to be false
    end
  end

  describe "#update_heartbeat!" do
    it "updates last_heartbeat to current time" do
      site = create(:site, last_heartbeat: 1.hour.ago)
      before_update = Time.current

      site.update_heartbeat!

      expect(site.last_heartbeat).to be >= before_update
      expect(site.last_heartbeat).to be_within(2.seconds).of(Time.current)
    end

    it "sets status to healthy when no anomalies" do
      site = create(:site, status: :unknown)
      site.update_heartbeat!
      expect(site.status).to eq("healthy")
    end

    it "sets status to critical when critical anomalies exist" do
      site = create(:site)
      create(:anomaly, :critical, site: site)
      site.update_heartbeat!
      expect(site.status).to eq("critical")
    end

    it "sets status to warning when warning anomalies exist" do
      site = create(:site)
      create(:anomaly, site: site, severity: :warning)
      site.update_heartbeat!
      expect(site.status).to eq("warning")
    end
  end

  describe "#active_anomalies" do
    it "returns unresolved anomalies" do
      site = create(:site)
      active = create(:anomaly, site: site)
      resolved = create(:anomaly, :resolved, site: site)

      expect(site.active_anomalies).to include(active)
      expect(site.active_anomalies).not_to include(resolved)
    end
  end

  describe "authentication" do
    it "authenticates with correct secret" do
      site = create(:site, secret: "my-secret")
      expect(site.authenticate_secret("my-secret")).to be_truthy
    end

    it "rejects incorrect secret" do
      site = create(:site, secret: "my-secret")
      expect(site.authenticate_secret("wrong-secret")).to be_falsey
    end

    it "hashes the secret with bcrypt" do
      site = create(:site, secret: "my-secret")
      expect(site.secret_digest).not_to eq("my-secret")
      expect(site.secret_digest).to start_with("$2a$")
    end
  end
end
