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

ActiveRecord::Schema[8.1].define(version: 2025_11_10_192525) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "pg_catalog.plpgsql"
  enable_extension "vector"

  create_table "active_storage_attachments", force: :cascade do |t|
    t.bigint "blob_id", null: false
    t.datetime "created_at", null: false
    t.string "name", null: false
    t.bigint "record_id", null: false
    t.string "record_type", null: false
    t.index ["blob_id"], name: "index_active_storage_attachments_on_blob_id"
    t.index ["record_type", "record_id", "name", "blob_id"], name: "index_active_storage_attachments_uniqueness", unique: true
  end

  create_table "active_storage_blobs", force: :cascade do |t|
    t.bigint "byte_size", null: false
    t.string "checksum"
    t.string "content_type"
    t.datetime "created_at", null: false
    t.string "filename", null: false
    t.string "key", null: false
    t.text "metadata"
    t.string "service_name", null: false
    t.index ["key"], name: "index_active_storage_blobs_on_key", unique: true
  end

  create_table "active_storage_variant_records", force: :cascade do |t|
    t.bigint "blob_id", null: false
    t.string "variation_digest", null: false
    t.index ["blob_id", "variation_digest"], name: "index_active_storage_variant_records_uniqueness", unique: true
  end

  create_table "ai_analyses", force: :cascade do |t|
    t.jsonb "analysis_data", default: {}
    t.string "analysis_type"
    t.decimal "confidence_score"
    t.datetime "created_at", null: false
    t.boolean "high_confidence"
    t.string "image_hash"
    t.integer "inventory_item_id", null: false
    t.string "model_used"
    t.integer "processing_time_ms"
    t.text "prompt_used"
    t.text "response"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["inventory_item_id"], name: "index_ai_analyses_on_inventory_item_id"
    t.index ["user_id"], name: "index_ai_analyses_on_user_id"
  end

  create_table "audit_logs", force: :cascade do |t|
    t.string "action"
    t.datetime "created_at", null: false
    t.text "details"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["user_id"], name: "index_audit_logs_on_user_id"
  end

  create_table "brands", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.text "description"
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.index ["name"], name: "index_brands_on_name", unique: true
  end

  create_table "categories", force: :cascade do |t|
    t.boolean "active", default: true
    t.datetime "created_at", null: false
    t.text "description"
    t.json "metadata", default: {}
    t.string "name", null: false
    t.bigint "parent_id"
    t.string "slug", default: "", null: false
    t.integer "sort_order", default: 0
    t.datetime "updated_at", null: false
    t.index ["active"], name: "index_categories_on_active"
    t.index ["created_at"], name: "index_categories_on_created_at"
    t.index ["name"], name: "index_categories_on_name", unique: true
    t.index ["parent_id", "sort_order"], name: "index_categories_on_parent_id_and_sort_order"
    t.index ["parent_id"], name: "index_categories_on_parent_id"
    t.index ["slug"], name: "index_categories_on_slug", unique: true
  end

  create_table "chats", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.bigint "model_id"
    t.datetime "updated_at", null: false
    t.bigint "user_id"
    t.index ["model_id"], name: "index_chats_on_model_id"
    t.index ["user_id"], name: "index_chats_on_user_id"
  end

  create_table "clothing_analyses", force: :cascade do |t|
    t.decimal "confidence", precision: 3, scale: 2
    t.datetime "created_at", null: false
    t.bigint "image_blob_id", null: false
    t.integer "items_detected", default: 0
    t.jsonb "parsed_data", default: {}
    t.string "status", default: "completed", null: false
    t.datetime "updated_at", null: false
    t.bigint "user_id", null: false
    t.index ["created_at"], name: "index_clothing_analyses_on_created_at"
    t.index ["image_blob_id"], name: "index_clothing_analyses_on_image_blob_id"
    t.index ["status"], name: "index_clothing_analyses_on_status"
    t.index ["user_id"], name: "index_clothing_analyses_on_user_id"
  end

  create_table "export_jobs", force: :cascade do |t|
    t.datetime "completed_at"
    t.datetime "created_at", null: false
    t.string "file_format"
    t.datetime "requested_at"
    t.string "status"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["user_id"], name: "index_export_jobs_on_user_id"
  end

  create_table "failed_login_attempts", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.datetime "failed_at", null: false
    t.string "ip_address"
    t.datetime "updated_at", null: false
    t.bigint "user_id"
    t.index ["failed_at"], name: "index_failed_login_attempts_on_failed_at"
    t.index ["ip_address"], name: "index_failed_login_attempts_on_ip_address"
    t.index ["user_id"], name: "index_failed_login_attempts_on_user_id"
  end

  create_table "inventory_items", force: :cascade do |t|
    t.integer "brand_id"
    t.integer "category_id", null: false
    t.bigint "clothing_analysis_id"
    t.datetime "created_at", null: false
    t.text "description"
    t.vector "embedding_vector", limit: 1536
    t.datetime "last_worn_at"
    t.json "metadata", default: {}
    t.string "name", null: false
    t.date "purchase_date"
    t.decimal "purchase_price", precision: 8, scale: 2
    t.integer "status", default: 0
    t.bigint "subcategory_id"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.integer "wear_count", default: 0
    t.index "((metadata ->> 'color'::text))", name: "index_inventory_items_on_metadata_color", where: "((metadata ->> 'color'::text) IS NOT NULL)"
    t.index "((metadata ->> 'season'::text))", name: "index_inventory_items_on_metadata_season", where: "((metadata ->> 'season'::text) IS NOT NULL)"
    t.index "user_id, ((metadata ->> 'color'::text))", name: "index_inventory_items_on_user_metadata_color", where: "((metadata ->> 'color'::text) IS NOT NULL)"
    t.index "user_id, ((metadata ->> 'season'::text))", name: "index_inventory_items_on_user_metadata_season", where: "((metadata ->> 'season'::text) IS NOT NULL)"
    t.index ["brand_id"], name: "index_inventory_items_on_brand_id"
    t.index ["category_id"], name: "index_inventory_items_on_category_id"
    t.index ["clothing_analysis_id"], name: "index_inventory_items_on_clothing_analysis_id"
    t.index ["created_at"], name: "index_inventory_items_on_created_at"
    t.index ["embedding_vector"], name: "index_inventory_items_on_embedding_vector", opclass: :vector_cosine_ops, using: :hnsw
    t.index ["last_worn_at"], name: "index_inventory_items_on_last_worn_at"
    t.index ["status"], name: "index_inventory_items_on_status"
    t.index ["subcategory_id"], name: "index_inventory_items_on_subcategory_id"
    t.index ["user_id", "category_id", "status"], name: "index_inventory_items_on_user_category_status"
    t.index ["user_id", "category_id"], name: "index_inventory_items_on_user_id_and_category_id"
    t.index ["user_id", "created_at"], name: "index_inventory_items_on_user_id_and_created_at"
    t.index ["user_id", "last_worn_at"], name: "index_inventory_items_on_user_last_worn_at"
    t.index ["user_id", "status"], name: "index_inventory_items_on_user_status"
    t.index ["user_id", "wear_count"], name: "index_inventory_items_on_user_wear_count"
    t.index ["user_id"], name: "index_inventory_items_on_user_id"
    t.index ["wear_count"], name: "index_inventory_items_on_wear_count"
  end

  create_table "inventory_tags", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.integer "inventory_item_id", null: false
    t.integer "tag_id", null: false
    t.datetime "updated_at", null: false
    t.index ["inventory_item_id", "tag_id"], name: "index_inventory_tags_on_inventory_item_id_and_tag_id", unique: true
    t.index ["inventory_item_id"], name: "index_inventory_tags_on_inventory_item_id"
    t.index ["tag_id"], name: "index_inventory_tags_on_tag_id"
  end

  create_table "messages", force: :cascade do |t|
    t.bigint "chat_id", null: false
    t.text "content"
    t.datetime "created_at", null: false
    t.integer "input_tokens"
    t.bigint "model_id"
    t.integer "output_tokens"
    t.string "role", null: false
    t.bigint "tool_call_id"
    t.datetime "updated_at", null: false
    t.index ["chat_id"], name: "index_messages_on_chat_id"
    t.index ["model_id"], name: "index_messages_on_model_id"
    t.index ["role"], name: "index_messages_on_role"
    t.index ["tool_call_id"], name: "index_messages_on_tool_call_id"
  end

  create_table "models", force: :cascade do |t|
    t.jsonb "capabilities", default: []
    t.integer "context_window"
    t.datetime "created_at", null: false
    t.string "family"
    t.date "knowledge_cutoff"
    t.integer "max_output_tokens"
    t.jsonb "metadata", default: {}
    t.jsonb "modalities", default: {}
    t.datetime "model_created_at"
    t.string "model_id", null: false
    t.string "name", null: false
    t.jsonb "pricing", default: {}
    t.string "provider", null: false
    t.datetime "updated_at", null: false
    t.index ["capabilities"], name: "index_models_on_capabilities", using: :gin
    t.index ["family"], name: "index_models_on_family"
    t.index ["modalities"], name: "index_models_on_modalities", using: :gin
    t.index ["provider", "model_id"], name: "index_models_on_provider_and_model_id", unique: true
    t.index ["provider"], name: "index_models_on_provider"
  end

  create_table "outfit_items", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.integer "inventory_item_id", null: false
    t.datetime "last_worn_at"
    t.text "notes"
    t.integer "outfit_id", null: false
    t.integer "position"
    t.text "styling_notes"
    t.datetime "updated_at", null: false
    t.integer "worn_count", default: 0
    t.index ["inventory_item_id"], name: "index_outfit_items_on_inventory_item_id"
    t.index ["outfit_id", "inventory_item_id"], name: "index_outfit_items_unique", unique: true
    t.index ["outfit_id"], name: "index_outfit_items_on_outfit_id"
  end

  create_table "outfits", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.text "description"
    t.boolean "is_favorite"
    t.boolean "is_public"
    t.datetime "last_worn_at"
    t.jsonb "metadata", default: {}
    t.string "name"
    t.string "occasion"
    t.string "season"
    t.integer "status", default: 0
    t.string "temperature_range"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.string "weather_condition"
    t.integer "worn_count", default: 0
    t.index "((metadata ->> 'occasion'::text))", name: "index_outfits_on_occasion_metadata"
    t.index "((metadata ->> 'season'::text))", name: "index_outfits_on_season_metadata"
    t.index ["user_id", "status"], name: "index_outfits_on_user_id_and_status"
    t.index ["user_id"], name: "index_outfits_on_user_id"
  end

  create_table "refresh_tokens", force: :cascade do |t|
    t.boolean "blacklisted", default: false, null: false
    t.datetime "created_at", null: false
    t.datetime "expires_at", null: false
    t.string "token", null: false
    t.datetime "updated_at", null: false
    t.bigint "user_id", null: false
    t.index ["blacklisted"], name: "index_refresh_tokens_on_blacklisted"
    t.index ["expires_at"], name: "index_refresh_tokens_on_expires_at"
    t.index ["token"], name: "index_refresh_tokens_on_token", unique: true
    t.index ["user_id"], name: "index_refresh_tokens_on_user_id"
  end

  create_table "solid_cache_entries", force: :cascade do |t|
    t.integer "byte_size", null: false
    t.datetime "created_at", null: false
    t.binary "key", null: false
    t.bigint "key_hash", null: false
    t.binary "value", null: false
    t.index ["byte_size"], name: "index_solid_cache_entries_on_byte_size"
    t.index ["key_hash", "byte_size"], name: "index_solid_cache_entries_on_key_hash_and_byte_size"
    t.index ["key_hash"], name: "index_solid_cache_entries_on_key_hash", unique: true
  end

  create_table "tags", force: :cascade do |t|
    t.string "color", default: "#3B82F6"
    t.datetime "created_at", null: false
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.index ["name"], name: "index_tags_on_name", unique: true
  end

  create_table "tool_calls", force: :cascade do |t|
    t.jsonb "arguments", default: {}
    t.datetime "created_at", null: false
    t.bigint "message_id", null: false
    t.string "name", null: false
    t.string "tool_call_id", null: false
    t.datetime "updated_at", null: false
    t.index ["message_id"], name: "index_tool_calls_on_message_id"
    t.index ["name"], name: "index_tool_calls_on_name"
    t.index ["tool_call_id"], name: "index_tool_calls_on_tool_call_id", unique: true
  end

  create_table "user_profiles", force: :cascade do |t|
    t.text "bio"
    t.datetime "created_at", null: false
    t.string "location"
    t.text "preferences"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.string "website"
    t.index ["user_id"], name: "index_user_profiles_on_user_id"
  end

  create_table "users", force: :cascade do |t|
    t.boolean "admin", default: false, null: false
    t.datetime "confirmed_at"
    t.datetime "created_at", null: false
    t.string "email"
    t.string "first_name"
    t.string "gender_preference", default: "unisex"
    t.string "last_name"
    t.string "password_digest"
    t.datetime "updated_at", null: false
    t.index ["admin"], name: "index_users_on_admin"
    t.index ["created_at"], name: "index_users_on_created_at"
    t.index ["email"], name: "index_users_on_email", unique: true
    t.index ["gender_preference"], name: "index_users_on_gender_preference"
  end

  add_foreign_key "active_storage_attachments", "active_storage_blobs", column: "blob_id"
  add_foreign_key "active_storage_variant_records", "active_storage_blobs", column: "blob_id"
  add_foreign_key "ai_analyses", "inventory_items"
  add_foreign_key "ai_analyses", "users"
  add_foreign_key "audit_logs", "users"
  add_foreign_key "categories", "categories", column: "parent_id"
  add_foreign_key "chats", "models"
  add_foreign_key "chats", "users"
  add_foreign_key "clothing_analyses", "users"
  add_foreign_key "export_jobs", "users"
  add_foreign_key "failed_login_attempts", "users"
  add_foreign_key "inventory_items", "brands"
  add_foreign_key "inventory_items", "categories"
  add_foreign_key "inventory_items", "categories", column: "subcategory_id"
  add_foreign_key "inventory_items", "clothing_analyses"
  add_foreign_key "inventory_items", "users"
  add_foreign_key "inventory_tags", "inventory_items"
  add_foreign_key "inventory_tags", "tags"
  add_foreign_key "messages", "chats"
  add_foreign_key "messages", "models"
  add_foreign_key "messages", "tool_calls"
  add_foreign_key "outfit_items", "inventory_items"
  add_foreign_key "outfit_items", "outfits"
  add_foreign_key "outfits", "users"
  add_foreign_key "refresh_tokens", "users"
  add_foreign_key "tool_calls", "messages"
  add_foreign_key "user_profiles", "users"
end
