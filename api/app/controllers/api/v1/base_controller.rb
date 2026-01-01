module Api
  module V1
    class BaseController < ApplicationController
      include Authenticatable

      # JSON:API content type
      before_action :set_content_type

      private

      def set_content_type
        response.headers["Content-Type"] = "application/vnd.api+json"
      end

      def render_jsonapi_error(message, status:, code: nil)
        render json: {
          errors: [ {
            status: Rack::Utils.status_code(status).to_s,
            code: code,
            title: status.to_s.titleize.gsub("_", " "),
            detail: message
          } ]
        }, status: status
      end

      def render_jsonapi_errors(errors, status:)
        render json: {
          errors: errors.map do |error|
            {
              status: Rack::Utils.status_code(status).to_s,
              title: "Validation Error",
              detail: error
            }
          end
        }, status: status
      end
    end
  end
end
