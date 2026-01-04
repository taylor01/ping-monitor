require "rails_helper"

RSpec.describe User, type: :model do
  describe "validations" do
    subject { build(:user) }

    it { should validate_presence_of(:email) }
    it { should validate_uniqueness_of(:email) }
    it { should allow_value("test@example.com").for(:email) }
    it { should_not allow_value("invalid-email").for(:email) }
  end

  describe "#can_authenticate?" do
    it "returns true for all users" do
      user = build(:user)
      expect(user.can_authenticate?).to be true
    end
  end

  describe "#available_scopes" do
    context "with admin role" do
      let(:user) { build(:user, role: :admin) }

      it "returns wildcard scope" do
        expect(user.available_scopes).to eq(%w[*])
      end
    end

    context "with operator role" do
      let(:user) { build(:user, role: :operator) }

      it "returns limited scopes including write" do
        expect(user.available_scopes).to eq(%w[sites:read anomalies:read anomalies:write])
      end
    end

    context "with viewer role" do
      let(:user) { build(:user, role: :viewer) }

      it "returns read-only scopes" do
        expect(user.available_scopes).to eq(%w[sites:read anomalies:read])
      end
    end
  end

  describe "#validate_scopes" do
    context "with admin role" do
      let(:user) { build(:user, role: :admin) }

      it "returns all requested scopes (wildcard)" do
        result = user.validate_scopes(%w[sites:read sites:write custom:scope])
        expect(result).to eq(%w[*])
      end
    end

    context "with operator role" do
      let(:user) { build(:user, role: :operator) }

      it "filters out unavailable scopes" do
        result = user.validate_scopes(%w[sites:read sites:write anomalies:read])
        expect(result).to eq(%w[sites:read anomalies:read])
      end

      it "includes available write scopes" do
        result = user.validate_scopes(%w[anomalies:read anomalies:write])
        expect(result).to eq(%w[anomalies:read anomalies:write])
      end
    end

    context "with viewer role" do
      let(:user) { build(:user, role: :viewer) }

      it "filters out write scopes" do
        result = user.validate_scopes(%w[sites:read anomalies:read anomalies:write])
        expect(result).to eq(%w[sites:read anomalies:read])
      end
    end

    context "with blank requested scopes" do
      let(:user) { build(:user, role: :operator) }

      it "returns available_scopes" do
        expect(user.validate_scopes(nil)).to eq(user.available_scopes)
        expect(user.validate_scopes([])).to eq(user.available_scopes)
      end
    end
  end

  describe "roles" do
    it "defaults to viewer role" do
      user = User.new(email: "test@example.com", password: "password")
      expect(user.role).to eq("viewer")
    end

    it "supports viewer, operator, and admin roles" do
      %w[viewer operator admin].each do |role|
        user = build(:user, role: role)
        expect(user.role).to eq(role)
      end
    end
  end
end
