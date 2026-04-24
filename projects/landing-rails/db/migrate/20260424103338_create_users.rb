class CreateUsers < ActiveRecord::Migration[8.1]
  def change
    # if_not_exists so both landing-rails and almirah-rails can carry this
    # migration without colliding — they share the same public.users table.
    create_table :users, if_not_exists: true do |t|
      t.string :email_address, null: false
      # password_digest is nullable to support Google-auth-only users.
      t.string :password_digest

      # OAuth columns — populated on Google sign-in, nil for email+password users.
      t.string :name
      t.string :provider
      t.string :uid

      # admin flag — mirrors the legacy public.admins allowlist. Set by the
      # SeedAdmins migration and the OmniAuth callback when the signing-in
      # user's email appears in public.admins.
      t.boolean :admin, default: false, null: false

      t.timestamps
    end

    add_index :users, :email_address, unique: true, if_not_exists: true
    add_index :users, [ :provider, :uid ], unique: true,
                                           where: "provider IS NOT NULL",
                                           if_not_exists: true
  end
end
