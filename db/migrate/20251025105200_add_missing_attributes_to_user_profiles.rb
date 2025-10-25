class AddMissingAttributesToUserProfiles < ActiveRecord::Migration[8.1]
  def change
    add_column :user_profiles, :location, :string
  end
end
