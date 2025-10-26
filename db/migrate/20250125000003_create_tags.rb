class CreateTags < ActiveRecord::Migration[8.1]
  def change
    create_table :tags do |t|
      t.string :name, null: false
      t.string :color, default: '#3B82F6'

      t.timestamps
    end

    add_index :tags, :name, unique: true
  end
end
