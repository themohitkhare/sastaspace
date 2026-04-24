class CreateUsers < ActiveRecord::Migration[8.1]
  def change
    create_table :users do |t|
      t.string :email_address, null: false
      # password_digest is nullable to support Google-auth-only users.
      t.string :password_digest

      # OAuth columns — populated on Google sign-in, nil for email+password users.
      t.string :name
      t.string :provider
      t.string :uid

      t.timestamps
    end

    add_index :users, :email_address, unique: true
    add_index :users, [ :provider, :uid ], unique: true, where: "provider IS NOT NULL"
  end
end
