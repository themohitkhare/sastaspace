class AddMoreMissingAttributesToUserProfiles < ActiveRecord::Migration[8.1]
  def change
    add_column :user_profiles, :website, :string
  end
end
