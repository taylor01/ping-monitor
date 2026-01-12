module Api
  module V1
    class InferredTopologiesController < BaseController
      # GET /api/v1/inferred_topologies
      # Get topology for a site (as hash)
      def index
        unless params[:site_name].present?
          return render_jsonapi_error("site_name parameter is required", status: :bad_request)
        end

        site = Site.find_by!(name: params[:site_name])
        topologies = policy_scope(InferredTopology).where(site: site)

        # Return as hash format for NC
        if params[:format] == "hash"
          topology_hash = InferredTopology.as_hash(site: site)
          render json: { data: topology_hash }
        else
          render json: InferredTopologySerializer.new(topologies).serializable_hash
        end
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      end

      # GET /api/v1/inferred_topologies/for_device
      # Get downstream devices for an upstream device
      def for_device
        unless params[:site_name].present? && params[:upstream_device].present?
          return render_jsonapi_error("site_name and upstream_device parameters are required", status: :bad_request)
        end

        site = Site.find_by!(name: params[:site_name])
        downstream = InferredTopology.downstream_for(
          site: site,
          upstream_device: params[:upstream_device]
        )

        render json: { data: { downstream_devices: downstream } }
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      end

      # POST /api/v1/inferred_topologies
      # NC records topology inference
      def create
        site = Site.find_by!(name: topology_params[:site_name])

        authorize InferredTopology.new(site: site)

        InferredTopology.record!(
          site: site,
          upstream_device: topology_params[:upstream_device],
          downstream_devices: topology_params[:downstream_devices]
        )

        # Return updated topology for the upstream device
        topologies = InferredTopology.where(
          site: site,
          upstream_device: topology_params[:upstream_device]
        )

        render json: InferredTopologySerializer.new(topologies).serializable_hash, status: :created
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      rescue ActiveRecord::RecordInvalid => e
        render_jsonapi_error(e.message, status: :unprocessable_entity)
      end

      private

      def topology_params
        params.permit(
          :site_name,
          :upstream_device,
          downstream_devices: []
        )
      end
    end
  end
end
