# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2025_12_31_235344) do
  create_table "analysis_logs", force: :cascade do |t|
    t.text "analysis_text"
    t.integer "anomaly_id", null: false
    t.string "claude_model"
    t.integer "completion_tokens"
    t.datetime "created_at", null: false
    t.integer "prompt_tokens"
    t.json "recommended_actions"
    t.json "tool_calls"
    t.string "trigger_type"
    t.datetime "updated_at", null: false
    t.index ["anomaly_id"], name: "index_analysis_logs_on_anomaly_id"
  end

  create_table "anomalies", force: :cascade do |t|
    t.integer "anomaly_type", null: false
    t.float "baseline_value"
    t.json "context_snapshot"
    t.datetime "created_at", null: false
    t.float "current_value"
    t.string "host"
    t.integer "measurement_id"
    t.text "message"
    t.datetime "resolved_at"
    t.integer "severity", null: false
    t.integer "site_id", null: false
    t.datetime "updated_at", null: false
    t.index ["measurement_id"], name: "index_anomalies_on_measurement_id"
    t.index ["resolved_at"], name: "index_anomalies_on_resolved_at"
    t.index ["severity", "created_at"], name: "index_active_anomalies_by_severity", where: "resolved_at IS NULL"
    t.index ["site_id", "created_at"], name: "index_anomalies_on_site_id_and_created_at"
    t.index ["site_id"], name: "index_anomalies_on_site_id"
  end

  create_table "baselines", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "host", null: false
    t.string "ip"
    t.float "latency_mean"
    t.float "latency_p95"
    t.float "latency_p99"
    t.float "latency_stddev"
    t.integer "sample_count", default: 0
    t.integer "site_id", null: false
    t.datetime "updated_at", null: false
    t.datetime "window_end"
    t.datetime "window_start"
    t.index ["site_id", "host"], name: "index_baselines_on_site_id_and_host", unique: true
    t.index ["site_id"], name: "index_baselines_on_site_id"
  end

  create_table "measurements", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "host", null: false
    t.string "ip", null: false
    t.boolean "is_up", null: false
    t.float "jitter_ms"
    t.float "latency_ms"
    t.float "packet_loss"
    t.integer "site_id", null: false
    t.datetime "timestamp", null: false
    t.datetime "updated_at", null: false
    t.index ["site_id", "host", "timestamp"], name: "index_measurements_on_site_id_and_host_and_timestamp"
    t.index ["site_id", "timestamp"], name: "index_measurements_on_site_id_and_timestamp"
    t.index ["site_id"], name: "index_measurements_on_site_id"
    t.index ["timestamp"], name: "index_measurements_on_timestamp"
  end

  create_table "sites", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.datetime "last_heartbeat"
    t.string "name"
    t.string "secret_digest"
    t.string "status"
    t.json "topology_data"
    t.datetime "updated_at", null: false
    t.index ["name"], name: "index_sites_on_name", unique: true
  end

  add_foreign_key "analysis_logs", "anomalies"
  add_foreign_key "anomalies", "measurements"
  add_foreign_key "anomalies", "sites"
  add_foreign_key "baselines", "sites"
  add_foreign_key "measurements", "sites"
end
