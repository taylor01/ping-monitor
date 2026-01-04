require "rails_helper"

RSpec.describe ApplicationPolicy do
  let(:site) { create(:site) }
  let(:user) { create(:user) }
  let(:record) { create(:site) }

  describe "default permissions" do
    subject { described_class.new(user, record) }

    it "denies index by default" do
      expect(subject.index?).to be false
    end

    it "denies show by default" do
      expect(subject.show?).to be false
    end

    it "denies create by default" do
      expect(subject.create?).to be false
    end

    it "denies update by default" do
      expect(subject.update?).to be false
    end

    it "denies destroy by default" do
      expect(subject.destroy?).to be false
    end
  end

  describe "helper methods" do
    context "when authenticatable is a Site" do
      subject { described_class.new(site, record) }

      it "identifies as site" do
        expect(subject.send(:site?)).to be true
        expect(subject.send(:user?)).to be false
        expect(subject.send(:agent?)).to be false
        expect(subject.send(:api_client?)).to be false
      end
    end

    context "when authenticatable is a User" do
      subject { described_class.new(user, record) }

      it "identifies as user" do
        expect(subject.send(:site?)).to be false
        expect(subject.send(:user?)).to be true
        expect(subject.send(:agent?)).to be false
        expect(subject.send(:api_client?)).to be false
      end

      context "with admin role" do
        let(:user) { create(:user, role: :admin) }

        it "identifies as admin" do
          expect(subject.send(:admin?)).to be true
          expect(subject.send(:operator?)).to be true
        end
      end

      context "with operator role" do
        let(:user) { create(:user, role: :operator) }

        it "identifies as operator but not admin" do
          expect(subject.send(:admin?)).to be false
          expect(subject.send(:operator?)).to be true
        end
      end

      context "with viewer role" do
        let(:user) { create(:user, role: :viewer) }

        it "is neither admin nor operator" do
          expect(subject.send(:admin?)).to be false
          expect(subject.send(:operator?)).to be false
        end
      end
    end

    context "when authenticatable is an Agent" do
      let(:agent) { create(:agent) }
      subject { described_class.new(agent, record) }

      it "identifies as agent" do
        expect(subject.send(:site?)).to be false
        expect(subject.send(:user?)).to be false
        expect(subject.send(:agent?)).to be true
        expect(subject.send(:api_client?)).to be false
      end
    end

    context "when authenticatable is an ApiClient" do
      let(:api_client) { create(:api_client) }
      subject { described_class.new(api_client, record) }

      it "identifies as api_client" do
        expect(subject.send(:site?)).to be false
        expect(subject.send(:user?)).to be false
        expect(subject.send(:agent?)).to be false
        expect(subject.send(:api_client?)).to be true
      end
    end
  end

  describe ApplicationPolicy::Scope do
    it "raises NotImplementedError when resolve is not defined" do
      scope = described_class.new(user, Site.all)
      expect { scope.resolve }.to raise_error(NotImplementedError)
    end
  end
end
