class CreateRefreshTokens < ActiveRecord::Migration[8.1]
  def change
    create_table :refresh_tokens do |t|
      t.references :user, null: false, foreign_key: true, index: true
      t.string :token, null: false
      t.datetime :expires_at, null: false
      t.boolean :blacklisted, default: false, null: false

      t.timestamps
    end

    add_index :refresh_tokens, :token, unique: true
    add_index :refresh_tokens, :blacklisted
    add_index :refresh_tokens, :expires_at
  end
end
