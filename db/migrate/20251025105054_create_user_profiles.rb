class CreateUserProfiles < ActiveRecord::Migration[8.1]
  def change
    create_table :user_profiles do |t|
      t.references :user, null: false, foreign_key: true
      t.text :bio
      t.text :preferences

      # Consolidated from add_missing_attributes migrations
      t.string :location
      t.string :website

      t.timestamps
    end
  end
end
