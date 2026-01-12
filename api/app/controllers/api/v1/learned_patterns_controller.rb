module Api
  module V1
    class LearnedPatternsController < BaseController
      # GET /api/v1/learned_patterns
      # List learned patterns (optionally filtered by site/device)
      def index
        patterns = policy_scope(LearnedPattern)
                     .includes(:site)
                     .order(confidence: :desc)

        # Filter by site name
        if params[:site_name].present?
          site = Site.find_by(name: params[:site_name])
          patterns = patterns.where(site: site) if site
        end

        # Filter by device
        if params[:device].present?
          patterns = patterns.for_device(params[:device])
        end

        # Only confident patterns
        patterns = patterns.confident if params[:confident] == "true"

        render json: LearnedPatternSerializer.new(
          patterns,
          include: parse_includes
        ).serializable_hash
      end

      # GET /api/v1/learned_patterns/:id
      def show
        pattern = policy_scope(LearnedPattern).find(params[:id])
        render json: LearnedPatternSerializer.new(pattern, include: parse_includes).serializable_hash
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Learned pattern not found", status: :not_found)
      end

      # POST /api/v1/learned_patterns
      # NC or human records a pattern
      def create
        site = Site.find_by!(name: pattern_params[:site_name])

        pattern = LearnedPattern.record!(
          site: site,
          device: pattern_params[:device],
          pattern_type: pattern_params[:pattern_type],
          description: pattern_params[:description],
          time_pattern: pattern_params[:time_pattern]
        )

        authorize pattern

        render json: LearnedPatternSerializer.new(pattern).serializable_hash, status: :created
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Site not found", status: :not_found)
      rescue ActiveRecord::RecordInvalid => e
        render_jsonapi_error(e.message, status: :unprocessable_entity)
      end

      # DELETE /api/v1/learned_patterns/:id
      # Remove a learned pattern
      def destroy
        pattern = policy_scope(LearnedPattern).find(params[:id])
        authorize pattern

        pattern.destroy!
        head :no_content
      rescue ActiveRecord::RecordNotFound
        render_jsonapi_error("Learned pattern not found", status: :not_found)
      end

      private

      ALLOWED_INCLUDES = %w[site].freeze

      def parse_includes
        return [] unless params[:include].present?

        requested = params[:include].split(",").map(&:strip)
        requested.select { |inc| ALLOWED_INCLUDES.include?(inc) }.map(&:to_sym)
      end

      def pattern_params
        params.permit(
          :site_name,
          :device,
          :pattern_type,
          :description,
          :time_pattern
        )
      end
    end
  end
end
