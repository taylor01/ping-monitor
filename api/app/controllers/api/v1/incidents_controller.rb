module Api
  module V1
    class IncidentsController < BaseController
      # GET /api/v1/incidents
      # List incidents (scoped by policy)
      def index
        incidents = policy_scope(Incident)
                      .includes(:site)
                      .order(started_at: :desc)

        # Status filters
        case params[:status]
        when "active"
          incidents = incidents.active
        when "resolved"
          incidents = incidents.resolved
        when "pending_review"
          incidents = incidents.pending_review
        end

        # Since filter for polling
        if params[:since].present?
          begin
            since_time = Time.parse(params[:since])
            incidents = incidents.where("updated_at > ?", since_time)
          rescue ArgumentError
            return render_jsonapi_error("Invalid since parameter format", status: :bad_request)
          end
        end

        # Not reported filter (for morning summary)
        incidents = incidents.not_reported if params[:not_reported] == "true"

        incidents = incidents.limit(params[:limit] || 50)

        render json: IncidentSerializer.new(
          incidents,
          include: parse_includes
        ).serializable_hash
      end

      # GET /api/v1/incidents/:id
      def show
        incident = policy_scope(Incident).find(params[:id])
        render json: IncidentSerializer.new(incident, include: parse_includes).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Incident not found", status: :not_found)
      end

      # POST /api/v1/incidents
      # NC creates an incident when escalating
      def create
        site = Site.find_by!(name: incident_params[:site_name])
        incident = site.incidents.new(
          started_at: incident_params[:started_at] || Time.current,
          severity: incident_params[:severity] || "normal",
          devices_affected: incident_params[:devices_affected] || [],
          nc_root_cause_guess: incident_params[:nc_root_cause_guess]
        )

        authorize incident

        if incident.save
          render json: IncidentSerializer.new(incident).serializable_hash, status: :created
        else
          render_jsonapi_errors(incident.errors, status: :unprocessable_entity)
        end
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      end

      # PATCH /api/v1/incidents/:id
      # Update incident (NC updates summary, humans add root cause)
      def update
        incident = policy_scope(Incident).find(params[:id])
        authorize incident

        if incident.update(update_params)
          render json: IncidentSerializer.new(incident).serializable_hash
        else
          render_jsonapi_errors(incident.errors, status: :unprocessable_entity)
        end
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Incident not found", status: :not_found)
      end

      # PATCH /api/v1/incidents/:id/resolve
      # Mark incident as resolved
      def resolve
        incident = policy_scope(Incident).find(params[:id])
        authorize incident

        incident.resolve!(
          auto_recovered: params[:auto_recovered] || false,
          nc_summary: params[:nc_summary]
        )

        render json: IncidentSerializer.new(incident).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Incident not found", status: :not_found)
      end

      # PATCH /api/v1/incidents/:id/review
      # Human adds root cause review
      def review
        incident = policy_scope(Incident).find(params[:id])
        authorize incident

        incident.add_human_review!(
          root_cause: params[:root_cause],
          notes: params[:notes]
        )

        render json: IncidentSerializer.new(incident).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Incident not found", status: :not_found)
      end

      # PATCH /api/v1/incidents/:id/mark_reported
      # Mark incident as reported in morning summary
      def mark_reported
        incident = policy_scope(Incident).find(params[:id])
        authorize incident

        incident.mark_reported!

        render json: IncidentSerializer.new(incident).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Incident not found", status: :not_found)
      end

      private

      ALLOWED_INCLUDES = %w[site].freeze

      def parse_includes
        return [] unless params[:include].present?

        requested = params[:include].split(",").map(&:strip)
        requested.select { |inc| ALLOWED_INCLUDES.include?(inc) }.map(&:to_sym)
      end

      def incident_params
        params.permit(
          :site_name,
          :started_at,
          :severity,
          :nc_root_cause_guess,
          devices_affected: []
        )
      end

      def update_params
        params.permit(
          :nc_summary,
          :nc_root_cause_guess,
          :human_root_cause,
          :human_notes,
          devices_affected: []
        )
      end
    end
  end
end
