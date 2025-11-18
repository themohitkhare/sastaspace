class CreateOutfits < ActiveRecord::Migration[8.1]
  def change
    create_table :outfits do |t|
      t.references :user, null: false, foreign_key: true
      t.string :name
      t.string :occasion
      t.string :season
      t.boolean :is_favorite
      t.boolean :is_public
      
      # Consolidated from add_missing_attributes migrations
      t.text :description
      t.string :weather_condition
      t.string :temperature_range
      
      # Consolidated from enhance_outfit_management_system
      t.jsonb :metadata, default: {}
      t.integer :status, default: 0
      t.integer :worn_count, default: 0
      t.datetime :last_worn_at

      t.timestamps
    end
    
    # Indexes consolidated from enhance_outfit_management_system
    add_index :outfits, [ :user_id, :status ]
    add_index :outfits, "(metadata->>'occasion')", name: "index_outfits_on_occasion_metadata"
    add_index :outfits, "(metadata->>'season')", name: "index_outfits_on_season_metadata"
  end
end
