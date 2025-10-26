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

ActiveRecord::Schema[8.1].define(version: 2025_10_26_093221) do
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
    t.string "analysis_type"
    t.integer "clothing_item_id", null: false
    t.decimal "confidence_score"
    t.datetime "created_at", null: false
    t.boolean "high_confidence"
    t.string "image_hash"
    t.string "model_used"
    t.integer "processing_time_ms"
    t.text "prompt_used"
    t.text "response"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["clothing_item_id"], name: "index_ai_analyses_on_clothing_item_id"
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

  create_table "clothing_items", force: :cascade do |t|
    t.string "analysis_status"
    t.string "brand"
    t.string "category"
    t.string "color"
    t.datetime "created_at", null: false
    t.string "image_hash"
    t.datetime "last_analyzed_at"
    t.string "name"
    t.text "notes"
    t.string "occasion"
    t.decimal "price"
    t.date "purchase_date"
    t.string "season"
    t.string "size"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["user_id"], name: "index_clothing_items_on_user_id"
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

  create_table "inventory_items", force: :cascade do |t|
    t.integer "brand_id"
    t.integer "category_id", null: false
    t.datetime "created_at", null: false
    t.text "description"
    t.vector "embedding_vector", limit: 1536
    t.string "item_type", null: false
    t.datetime "last_worn_at"
    t.json "metadata", default: {}
    t.string "name", null: false
    t.date "purchase_date"
    t.decimal "purchase_price", precision: 8, scale: 2
    t.integer "status", default: 0
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.integer "wear_count", default: 0
    t.index ["brand_id"], name: "index_inventory_items_on_brand_id"
    t.index ["category_id"], name: "index_inventory_items_on_category_id"
    t.index ["created_at"], name: "index_inventory_items_on_created_at"
    t.index ["embedding_vector"], name: "index_inventory_items_on_embedding_vector", opclass: :vector_cosine_ops, using: :hnsw
    t.index ["item_type"], name: "index_inventory_items_on_item_type"
    t.index ["last_worn_at"], name: "index_inventory_items_on_last_worn_at"
    t.index ["status"], name: "index_inventory_items_on_status"
    t.index ["user_id", "category_id"], name: "index_inventory_items_on_user_id_and_category_id"
    t.index ["user_id", "created_at"], name: "index_inventory_items_on_user_id_and_created_at"
    t.index ["user_id", "item_type"], name: "index_inventory_items_on_user_id_and_item_type"
    t.index ["user_id"], name: "index_inventory_items_on_user_id"
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

  create_table "outfit_items", force: :cascade do |t|
    t.integer "clothing_item_id", null: false
    t.datetime "created_at", null: false
    t.text "notes"
    t.integer "outfit_id", null: false
    t.integer "position"
    t.datetime "updated_at", null: false
    t.index ["clothing_item_id"], name: "index_outfit_items_on_clothing_item_id"
    t.index ["outfit_id"], name: "index_outfit_items_on_outfit_id"
  end

  create_table "outfits", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.text "description"
    t.boolean "is_favorite"
    t.boolean "is_public"
    t.string "name"
    t.string "occasion"
    t.string "season"
    t.string "temperature_range"
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.string "weather_condition"
    t.index ["user_id"], name: "index_outfits_on_user_id"
  end

  create_table "tags", force: :cascade do |t|
    t.string "color", default: "#3B82F6"
    t.datetime "created_at", null: false
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.index ["name"], name: "index_tags_on_name", unique: true
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
    t.datetime "confirmed_at"
    t.datetime "created_at", null: false
    t.string "email"
    t.string "first_name"
    t.string "last_name"
    t.string "password_digest"
    t.datetime "updated_at", null: false
    t.index ["created_at"], name: "index_users_on_created_at"
    t.index ["email"], name: "index_users_on_email", unique: true
  end

  add_foreign_key "active_storage_attachments", "active_storage_blobs", column: "blob_id"
  add_foreign_key "active_storage_variant_records", "active_storage_blobs", column: "blob_id"
  add_foreign_key "ai_analyses", "clothing_items"
  add_foreign_key "ai_analyses", "users"
  add_foreign_key "audit_logs", "users"
  add_foreign_key "categories", "categories", column: "parent_id"
  add_foreign_key "clothing_items", "users"
  add_foreign_key "export_jobs", "users"
  add_foreign_key "inventory_items", "brands"
  add_foreign_key "inventory_items", "categories"
  add_foreign_key "inventory_items", "users"
  add_foreign_key "inventory_tags", "inventory_items"
  add_foreign_key "inventory_tags", "tags"
  add_foreign_key "outfit_items", "clothing_items"
  add_foreign_key "outfit_items", "outfits"
  add_foreign_key "outfits", "users"
  add_foreign_key "user_profiles", "users"
end
