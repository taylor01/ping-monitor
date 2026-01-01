FactoryBot.define do
  factory :analysis_log do
    anomaly
    trigger_type { "automatic" }
    claude_model { "claude-sonnet-4-20250514" }
    prompt_tokens { 500 }
    completion_tokens { 200 }
    analysis_text { "Analysis of the network issue..." }
    tool_calls { [] }
    recommended_actions { [ "Check router status", "Verify ISP connection" ] }
  end
end
