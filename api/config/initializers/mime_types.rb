# Register JSON:API MIME type
# This allows Rails to parse application/vnd.api+json as JSON
Mime::Type.register "application/vnd.api+json", :jsonapi

# Make Rails parse JSON:API content as JSON
ActionDispatch::Request.parameter_parsers[:jsonapi] = lambda do |raw_post|
  ActiveSupport::JSON.decode(raw_post)
end
