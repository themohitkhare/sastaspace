class AddGenderPreferenceToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :gender_preference, :string, default: "unisex"
    add_index :users, :gender_preference
  end
end
